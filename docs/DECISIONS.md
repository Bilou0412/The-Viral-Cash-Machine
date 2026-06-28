# DECISIONS — journal court

Une ligne par décision transverse (la plus récente en haut). Pour le plan d'exécution, voir
`ROADMAP.md`.

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
