# DECISIONS — journal court

Une ligne par décision transverse (la plus récente en haut). Pour le plan d'exécution, voir
`ROADMAP.md`.

- **2026-07-08** · **Rail unique** (fin de la bidouille) · un FORMAT = une STRUCTURE qui
  produit un `EditorDocument` v5 ; `compile_shot` compile TOUS les prompts, `describe_document`
  rend TOUT en texte, `document_to_spec` rend TOUT en `VideoSpec`. Aucun format ne construit
  ses prompts à la main. Conséquence : le **horror-CYOA migre sur v5** (l'adaptateur émet des
  `ShotBrief`, plus de briques blob) pour hériter qualité + descripteur + atelier agents.
  Règle écrite : `.claude/rules/architecture.md`.

- **2026-06-28** · Durcissement fait : **montage async** (BackgroundTask, plus de 502) +
  **R2 flux épisode** (storage port local/R2, serving proxifié par l'API). Reliquat : flux
  éditeur/briques sur R2 (chemins recalculés) avant scale horizontal. Cf. `docs/DEPLOY.md`.
- **2026-06-28** · Infra dev/prod sur **Fly.io** + **Postgres managé** + CD GitHub (push
  dev / tag prod) · 1 image Docker → 2 apps ; `engine.py` rendu dialect-agnostique (défaut
  SQLite intact). Détails et runbook : `docs/DEPLOY.md`.
- **2026-06-28** · Assets : **volume d'abord, R2 ensuite** (PR de durcissement) · le serving
  est déjà same-origin via `FileResponse` (vérifié) → R2 gardera ce proxy (pas d'URL signée
  au navigateur), ce qui évite tout le piège CORS/expiration.
- **2026-06-28** · Bug prod identifié à corriger avant trafic : `POST .../montage` est
  **synchrone** (MoviePy en requête) → 502 sur timeout Fly ~60s ; à passer en `BackgroundTasks`
  (cf. `docs/DEPLOY.md` « Étape suivante »). Non fait dans cet incrément (casse 2 tests à adapter).
- **2026-06-28** · Suppression de graphify (graphe + hooks + étape ROADMAP §7) · graphe bâti
  sur l'ancien `master` monolithe = décrivait du code mort ; à ~20K LOC bien rangées,
  l'arborescence nommée est déjà un index fiable et toujours à jour.
- **2026-06-28** · CLAUDE.md réécrit en *carte navigable* (archi feature-driven réelle,
  pointeur ROADMAP, boucle `make verify`) · l'ancien décrivait le Streamlit monolithe →
  fausse carte à chaque session.
- **2026-06-28** · Plans supersédés déplacés dans `docs/archive/` · ne garder à la racine
  qu'**un** plan vivant (`ROADMAP.md`) pour réduire le bruit de contexte.
- **2026-06-28** · Contexte découpé : CLAUDE.md léger + `.claude/rules/` path-scopées
  (backend/frontend/tests) + skills `/resume` et `/verify` + hook `SessionStart` · charger le
  contexte à la demande plutôt qu'en bloc.
- **2026-06-28** · Stack confirmée (Python/FastAPI + React/TS + Remotion) · pas de migration
  Django/Angular ; l'archi actuelle est déjà « AI-friendly ».
