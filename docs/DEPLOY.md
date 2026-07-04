# DEPLOY — deux environnements Fly.io (dev + prod)

Cible : **Fly.io** (1 image Docker → 2 apps), **Postgres managé**, assets sur **volume**
(R2 en étape suivante), **CD GitHub Actions** (push `dev` → dev ;
tag `v*` → prod).

> Le repo ne déploie rien tout seul : la config est inerte tant que tu n'as pas exécuté le
> runbook ci-dessous (comptes + secrets côté Fly/Cloudflare).

## Architecture

```
GitHub  ──push branche dev──▶  deploy.yml ──flyctl──▶  vcm-studio-dev  ─┐
        ──tag v*───────────▶  deploy.yml ──flyctl──▶  vcm-studio-prod ─┤
                                                                       ├─▶ Postgres managé (par env)
1 image Docker (Dockerfile) = FastAPI + front React buildé + Remotion  │
  • DB        : DATABASE_URL (Postgres)        ← secret Fly             │
  • assets    : /data/studio_output (volume)   ← R2 en étape suivante ──┘
  • secrets   : OPENAI_API_KEY, REPLICATE_API_TOKEN ← fly secrets
```

Ce qui est **déjà câblé dans le code** (cette PR) :
- `src/studio/db/engine.py` lit `VCM_STUDIO_DB` **puis** `DATABASE_URL`, réécrit
  `postgres://`→`postgresql+psycopg://`, et n'applique les options SQLite que sur SQLite.
  Driver `psycopg[binary]` ajouté. **Défaut partout = SQLite** (local/tests/CI inchangés).
- `src/studio/api/settings.py` : `CORS_ORIGINS` et `VCM_RENDER_BASE` pilotables par env.
- `fly.toml` (prod) / `fly.dev.toml` (dev) / `.github/workflows/deploy.yml` (CD).

## Runbook (une fois, côté auteur)

Pré-requis : `curl -L https://fly.io/install.sh | sh` puis `fly auth login` ; un compte
Cloudflare (pour R2, étape suivante).

```bash
# 1) Créer les 2 apps SANS écraser le Dockerfile multi-stage
fly launch --no-deploy --copy-config --name vcm-studio-prod --region cdg
fly launch --no-deploy --copy-config --name vcm-studio-dev  --region cdg --config fly.dev.toml
#   → refuser toute suggestion de Dockerfile/runtime : on garde l'existant.

# 2) Volumes persistants (/data : DB locale éventuelle + assets)
fly volumes create vcm_data     --size 10 --region cdg -a vcm-studio-prod
fly volumes create vcm_data_dev --size 5  --region cdg -a vcm-studio-dev

# 3) Postgres managé + attache (pose le secret DATABASE_URL et redémarre)
fly mpg create --name vcm-pg-prod --region cdg && fly mpg attach <clusterID-prod> -a vcm-studio-prod
fly mpg create --name vcm-pg-dev  --region cdg && fly mpg attach <clusterID-dev>  -a vcm-studio-dev
#   Alternative Neon/Supabase : fly secrets set DATABASE_URL='postgresql+psycopg://...' -a <app>

# 4) Secrets API (par app) — OPTIONNEL : les clés OpenAI/Replicate se saisissent
#    désormais DANS l'app (page Réglages, BYOK). fly secrets reste possible.
fly secrets set OPENAI_API_KEY=... REPLICATE_API_TOKEN=... -a vcm-studio-prod
fly secrets set OPENAI_API_KEY=... REPLICATE_API_TOKEN=... -a vcm-studio-dev

# 4bis) Auth (Phase B.1) — REQUIS : signature des cookies + compte admin bootstrap.
#   VCM_SESSION_SECRET : chaîne aléatoire (ex. `openssl rand -hex 32`).
#   VCM_ADMIN_EMAIL / VCM_ADMIN_PASSWORD : ton compte admin (créé au 1er démarrage
#   s'il n'existe pas). Sans eux : personne ne peut générer. (VCM_COOKIE_SECURE=1
#   est déjà dans [env] des fly.toml.)
fly secrets set VCM_SESSION_SECRET=... VCM_ADMIN_EMAIL=... VCM_ADMIN_PASSWORD=... -a vcm-studio-dev
fly secrets set VCM_SESSION_SECRET=... VCM_ADMIN_EMAIL=... VCM_ADMIN_PASSWORD=... -a vcm-studio-prod

# 5) Premier déploiement manuel + contrôle
fly deploy --remote-only --config fly.toml      # prod
fly deploy --remote-only --config fly.dev.toml  # dev
fly logs -a vcm-studio-prod                      # vérifier le healthcheck /api/projects

# 6) CD GitHub : token + secret repo
fly tokens create org
gh secret set FLY_API_TOKEN --body '<token>'
#   Ensuite : push sur dev → deploy dev ; merge dev->main + git tag v1.0.0 && git push --tags → deploy prod
```

Garde-fous :
- **Jamais** de secret (`DATABASE_URL`, clés API, `R2_*_KEY`) dans les `fly.toml` (commités) :
  uniquement via `fly secrets set`.
- **Ne pas `fly scale count > 1`** sur le web tant que les assets sont sur le volume :
  chaque machine a son propre `/data` → *split-brain* (404 assets). Voir « Étape suivante ».

## Durcissement « production-grade » — état

- ✅ **Montage asynchrone** — `POST /api/episodes/{id}/montage` valide les prérequis en
  synchrone (409 si pas d'assets) puis planifie le montage en `BackgroundTask` (plus de 502
  sur le timeout Fly).
- ✅ **Object storage R2 (flux épisode)** — `src/features/storage/` : `StoragePort` +
  `LocalStorage` (défaut, byte-identique) + `R2Storage` (boto3) + factory `STORAGE_BACKEND`.
  Câblé sur génération (persistance + idempotence), montage (materialize + persist) et
  serving (`/api/assets/{id}/file`, `/api/episodes/{id}/video` → `storage.serve`, proxifié
  par l'API, **pas d'URL signée au navigateur**). Activer avec les env R2 ci-dessous.
- ⬜ **R2 pour le flux ÉDITEUR/briques** (reliquat) — `editor_generation.py`,
  `remotion_render.py` et `GET /api/editor/documents/{id}/video` utilisent encore des chemins
  locaux recalculés (pas un ref stocké). À aligner sur le même port avant de servir le
  rendu briques depuis R2 / de scaler le web > 1 machine. (C'est le R-step R2 du ROADMAP.)

### Activer R2 (par app)
```bash
# Buckets : vcm-assets-prod / vcm-assets-dev. Token R2 « Object Read & Write » → noter
# Secret Access Key (affiché 1 fois) + Account ID (endpoint = https://<ACCOUNT_ID>.r2...).
fly secrets set R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... -a vcm-studio-prod
# Non-secrets dans [env] des fly.toml : STORAGE_BACKEND='r2', R2_ENDPOINT, R2_BUCKET,
# R2_PUBLIC_BASE (custom domain Cloudflare pour des URLs stables/cachées).
```
CORS bucket (si un jour on sert R2 directement au navigateur, pas le cas actuel — on
proxifie) : AllowedOrigins = origine front exacte, AllowedMethods GET/HEAD, ExposeHeaders
`Content-Range, Accept-Ranges, Content-Length, ETag`. Tant qu'on proxifie via l'API,
aucune config CORS R2 n'est requise.

> **Scale horizontal** : possible une fois (a) DB=Postgres (fait) **et** (b) flux éditeur
> aussi sur R2 (reliquat ci-dessus). Avant ça, garder le web à **1 machine**.

Migrations de schéma : aujourd'hui `create_all` (schéma neuf OK). Dès la 2ᵉ évolution de
schéma en prod, introduire **Alembic** (+ `release_command = "alembic upgrade head"` dans
`fly.toml`, avec une `DATABASE_URL` directe non poolée pour la migration).
