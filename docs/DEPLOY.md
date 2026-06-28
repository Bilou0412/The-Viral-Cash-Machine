# DEPLOY — deux environnements Fly.io (dev + prod)

Cible : **Fly.io** (1 image Docker → 2 apps), **Postgres managé**, assets sur **volume**
(R2 en étape suivante), **CD GitHub Actions** (push `refactor/feature-driven` → dev ;
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

# 4) Secrets API (par app)
fly secrets set OPENAI_API_KEY=... REPLICATE_API_TOKEN=... -a vcm-studio-prod
fly secrets set OPENAI_API_KEY=... REPLICATE_API_TOKEN=... -a vcm-studio-dev

# 5) Premier déploiement manuel + contrôle
fly deploy --remote-only --config fly.toml      # prod
fly deploy --remote-only --config fly.dev.toml  # dev
fly logs -a vcm-studio-prod                      # vérifier le healthcheck /api/projects

# 6) CD GitHub : token + secret repo
fly tokens create org
gh secret set FLY_API_TOKEN --body '<token>'
#   Ensuite : push refactor/feature-driven → deploy dev ; git tag v1.0.0 && git push --tags → deploy prod
```

Garde-fous :
- **Jamais** de secret (`DATABASE_URL`, clés API, `R2_*_KEY`) dans les `fly.toml` (commités) :
  uniquement via `fly secrets set`.
- **Ne pas `fly scale count > 1`** sur le web tant que les assets sont sur le volume :
  chaque machine a son propre `/data` → *split-brain* (404 assets). Voir « Étape suivante ».

## Étape suivante (PR de durcissement « production-grade »)

Deux chantiers identifiés et **vérifiés** par la conception, à finir avant d'ouvrir le
trafic prod / d'activer l'autoscaling :

1. **Object storage R2 (assets)** — introduire un *storage port* (`src/features/storage/`)
   avec backends `local` (défaut) et `r2` (boto3), servir les fichiers **proxifiés par
   l'API** (on garde le same-origin `FileResponse`/redirect, pas d'URL signée au
   navigateur → zéro piège CORS). Débloque le scale horizontal (web stateless).
2. **Montage asynchrone** — `POST /api/episodes/{id}/montage` exécute aujourd'hui MoviePy
   **dans la requête** (plusieurs minutes) → **502 garanti** sur le timeout proxy Fly ~60s.
   Le passer en `BackgroundTasks` + événements SSE comme `produce`/`render` (valider les
   prérequis en synchrone pour conserver le 409, puis planifier). Touche 2 tests à adapter.

Migrations de schéma : aujourd'hui `create_all` (schéma neuf OK). Dès la 2ᵉ évolution de
schéma en prod, introduire **Alembic** (+ `release_command = "alembic upgrade head"` dans
`fly.toml`, avec une `DATABASE_URL` directe non poolée pour la migration).
