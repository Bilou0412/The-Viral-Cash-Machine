---
paths:
  - "frontend/**"
---

# Frontend React/TS — règles

- **Stack** : React + TypeScript + Vite + Tailwind. Composants UI dans
  `src/components/` (`editor/`, `studio/`, `ui/`), pages dans `src/pages/`, accès API dans
  `src/lib/api.ts`, hooks dans `src/hooks/`.
- **Le front est une surface de REVUE de briques, pas un éditeur de montage vierge.** On
  déplie l'arbre de `ClipBrick` généré par l'IA, on édite ses **args** (`form_descriptor`) et
  son agencement, on régénère **ciblé**. (La revue en timeline multipiste — ex-étape R2 — est faite.)
- **Recibler l'existant** : réutiliser `src/components/editor/` (Timeline, BrickPalette,
  Inspector) en les branchant sur les `ClipBrick` composites, plutôt que de repartir des
  briques plates legacy.
- **Mode mock** : `VITE_USE_MOCKS=true` fait tourner le front sans backend Python (cf. tests
  e2e Playwright). Garder les mocks (`src/lib/mocks.ts`) cohérents avec les types
  (`src/lib/types.ts`).
- **Avant commit** : `cd frontend && npm run build` (tsc + vite) doit passer ; `make e2e`
  pour les tests navigateur.
