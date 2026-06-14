# AUTONOMY_PLAN — harnais de vérification pour développer en boucle (sans l'auteur)

## Constat (le goulot actuel)
La boucle est : *Claude édite → l'auteur rebuild Docker → l'auteur clique l'UI →
l'auteur colle les logs → Claude corrige*. L'auteur EST le harnais de test. Les bugs
récents (403 Cloudflare, lanes invisibles, intro absente, repli montage silencieux)
n'ont été vus QUE parce que l'auteur a testé à la main. Cause racine : **je ne peux pas
exécuter l'app de bout en bout moi-même** (deps lourdes — sqlalchemy/moviepy/node/
chromium — absentes de l'hôte ; le code vit dans l'image Docker, pas en live).

## Objectif
Un **harnais que JE lance** (`make verify`) qui exerce l'app **de fond en comble** et me
rend un rapport PASS/FAIL exploitable — pour itérer en boucle auto, l'auteur ne validant
qu'aux jalons. + une **vision précise et testable** (north star) pour ne pas dériver.

---

## V1 — Pouvoir exécuter l'app (env de dev pilotable)
Lever le blocage « deps Docker-only ».
- **`requirements-dev.txt`** (pytest, mypy, ruff, + les runtime deps testables) et/ou un
  **compose de dev** `docker-compose.dev.yml` qui **monte le code source** (`./src:/app/src`,
  `./tests:/app/tests`) → éditer = live, pas de rebuild. Image = celle existante (a déjà
  ffmpeg/node/chromium).
- **Scripts** (`Makefile` ou `scripts/`): `make test` (pytest COMPLET dans le conteneur,
  via `docker compose -f …dev exec`), `make typecheck` (mypy propre, remplace le venv
  jetable `/tmp/mypyenv`), `make lint`, `make build-front`.
- Résultat : je lance la **vraie** suite (y compris `test_studio_db/api/editor_api`,
  golden montage) sans toi.

## V2 — Tests d'intégration API + chemin « fake render » (offline)
- **Smoke API** : booter l'app (TestClient) et **taper chaque route** avec un payload
  minimal + fakes → **aucun 500** (aurait attrapé le 403/500 du catalogue tout de suite).
- **Parcours éditeur offline** (étend `test_editor_api`) : projet → doc → poser briques →
  connexions → générer (FakeAssetProvider) → `render-model` cohérent → assets persistés.
- **`VCM_FAKE_RENDER=1`** : un renderer bouchon qui écrit un petit MP4 sans Chromium →
  le parcours « Rendre » est testable en boucle ; le **vrai** render Remotion reste un
  smoke séparé (gated, V3).
- **Catalogue modèles** : un mode `VCM_FAKE_CATALOG=1` (schémas factices) pour tester
  l'inspecteur sans réseau Replicate.

## V3 — E2E navigateur (ce que fait l'auteur aujourd'hui)
- **Playwright** (headless, chromium déjà dans l'image). Scénarios = les parcours réels :
  créer projet → nouvel épisode (thème+N) ; ouvrir l'éditeur → **poser une brique**
  (drag + clic) → vérifier qu'elle est **visible** sur une lane → cliquer → l'inspecteur
  charge les **arguments du modèle** → connecter deux briques → générer (fake) → aperçu.
- **Assertions de santé** : **0 réponse 4xx/5xx** dans le réseau, **0 erreur console**,
  + **captures d'écran** par étape (je les lis). C'est l'outil qui aurait vu « lanes
  invisibles » et « form 502 » sans toi.
- Deux modes : `VITE_USE_MOCKS=1` (front pur, rapide) et **stack réelle** (API+fakes).

## V4 — Préciser la vision : SPEC testable (north star)
« Prolonger mais surtout préciser » = transformer la vision en **critères d'acceptation
testables**, fichier `SPEC.md` :
- **Ce que l'app EST** : éditeur timeline (palette → poser/placer/durer → inspecteur tous
  args → connexions → contexte → générer à la demande → rendre) + format Aventure (intro
  obligatoire, N séquences, outro).
- **Invariants** (chacun ↔ un test) : « composer ne génère rien » ; « tout argument de
  modèle est éditable » ; « une nouvelle timeline montre toujours des lanes » ; « intro
  toujours présente quel que soit le chemin » ; « repli montage jamais silencieux » ; etc.
- **Parcours utilisateur** numérotés → chacun = **1 test E2E Playwright**.
- **Definition of Done** par feature : types OK + pytest vert + lint + parcours E2E vert.
Le SPEC devient la **source des tests** : ajouter une feature = ajouter son critère + son E2E.

## V5 — La boucle + le rapport
- **`make verify`** = mypy + pytest complet + build front + smoke API + E2E Playwright →
  **un rapport compact PASS/FAIL** (+ chemins des captures) que je parse en un coup d'œil.
- **Boucle auto** (via `/loop` ou un Workflow) : éditer → `verify` → lire les échecs →
  corriger → recommencer, jusqu'au vert. L'auteur ne voit que les **jalons** (ou un
  récap + captures), plus les allers-retours de logs.
- **CI GitHub Actions** (même `verify`) → filet permanent.

---

## Ce que ça change concrètement
Avant : *Claude → (toi: rebuild+clic+logs) → Claude*. Après : *Claude → `make verify`
(suite + API + navigateur + captures) → Claude*, en boucle. Toi = **directeur créatif**
qui valide les jalons et tranche la vision, plus le testeur manuel.

## Ordre proposé
V1 (déblocage exécution) → V2 (intégration + fake render/catalog) → V4 (SPEC, en parallèle,
car il guide les tests) → V3 (Playwright E2E) → V5 (verify + boucle + CI).
Démarrage conseillé : **V1 + un premier `make verify`** (mypy+pytest+build) tout de suite —
gain immédiat — puis V3 (Playwright) qui supprime vraiment ta phase de clic.
