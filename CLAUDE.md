# CLAUDE.md

Guidance for Claude Code working in this repository. Keep this file a **map + pointers**,
not a copy of the code. Modèle de branches : **`main`** (canonique, protégée) ←
PR depuis **`dev`** (branche de développement, on push ici). Une release = merge
`dev`→`main` puis tag `v*` (déploie prod). `master` = ancien monolithe, archivé.

## Reprendre le travail (« reprends » / « resume »)

La **source unique de vérité** est **`ROADMAP.md`**. Pour reprendre : ouvrir `ROADMAP.md`,
lire **§4 (état consolidé, déjà fait)** puis **§5 (étapes restantes)** — la première ligne
⬜ = la prochaine étape (actuellement **S1 — fermer la boucle réelle / dogfood**). **Une étape
par session**, protocole de l'étape en **§7**. Direction produit tranchée : **« l'IA écrit → je
révise en briques »**, pas un éditeur de montage vierge ; happy path = **« Créer » (idée → scènes)**.

## Le produit en une phrase

**Créateur de vidéos verticales 9:16** pour TikTok/Shorts/Reels. Une vidéo = une séquence de
**SCÈNES** (contexte concentré : photo d'environnement + plans courts qui l'animent + audio).
L'IA découpe l'idée en scènes puis en **briques éditables** (`ClipBrick` vidéo/photo + enfants
narration/dialogue), on **révise les briques** dans une UI React et on **ne régénère que ce
qu'on touche** (maîtrise du coût). Dialogues en **français**, prompts visuels en **anglais**.
Le format « aventure à choix » (CYOA) est un chemin legacy conservé, plus le happy path.

## Le rail (pipeline unique)

```
idée (page « Créer »)
  → [S-IA] get_scene_decomposer (Fake / OpenAI 2 phases) → VideoPlan   src/features/scenes/
  → [S-B]  scene_plan_to_document        → EditorDocument (briques + index scènes)  src/features/scenes/scene_plan_to_document.py
  → [R2]   UI de revue React (timeline multipiste Vidéo/Son + bandes de scène, éditer args, régénérer ciblé)   frontend/
  → [B1]   document_to_spec              → VideoSpec (IR)       src/editor/compile_spec.py
  → [IR]   resolve_real + MoviePyRenderEngine → MP4 final       src/videospec/
```
Rail legacy conservé (chemin aventure, plus le défaut) : `openai_adventure_decomposer →
adventure_to_bricks → document_to_spec` (`src/features/scripting/`).

## Carte du code (le vrai index — préférer la lecture ciblée d'un module au grep large)

Backend Python (`src/`, ~19,5k LOC, mypy strict par zones) :
- `src/features/` — features à **ports `typing.Protocol`** (impl Fake offline + réelle injectées) :
  - `scenes/` — **happy path** : décomposeur de scènes neutre (Fake / OpenAI 2 phases) + `scene_plan_to_document` + `split`.
  - `scripting/` — décomposeur **aventure legacy** (`adventure_to_video_plan`, prompts/themes).
  - `formats/` — couche **« moule »** (catalogue + dispatch), tous → même `EditorDocument` v5.
  - `crew/` — **agent réalisateur (TPLM-C)** : `DirectorAgent` → `FragmentPlan` → briques v5 (`assemble`). ⚠️ orphelin, à brancher.
  - `crew_room/` — atelier **scène-par-scène** (contrat → brouillons → merge → révision), câblé.
  - `brief/` — producteur (propose un brief). `virality/` — N hooks → prédiction → classement.
  - `performance/` — **moat** : perfs réelles → poids appris → recalibrage du prédicteur.
  - `publish/` — publication (port + Fake + route). `storage/` — Local/R2 + factory.
  - `assets/` (Replicate) · `transcription/` (Whisper) · `compositing/` (overlays, heads, srt, `registry` capacités + effets montage).
- `src/videospec/` — IR déclarative **`VideoSpec`** (immuable) + ports `RenderEngine`/
  `AssetResolver`, `render_moviepy.py`, `resolve_real.py`/`resolve_fake.py`.
- `src/editor/` — **`ClipBrick`** (`document.py`, v5 Vidéo→Scène→Plan + bibles),
  **`compile_shot.py`** (SEUL producteur de prompts image/motion), **`describe.py`** (descripteur unique),
  `document_to_spec` (`compile_spec.py`, effets = données IR), `capabilities.py` (`validate_clip`),
  `resolve.py`/`migrations.py` (briques plates legacy).
- `src/studio/api/` — backend **FastAPI** : `app.py`, `events.py` (SSE), `services/`
  (génération, `editor_generation`, montage, `model_catalog`, pricing…), `db/` (sqlmodel :
  models, repositories, migrate).
- `src/infra/` — `download.py`, `env.py`, `logging.py`. `src/pipeline.py` — séquence pure.
- `src/app.py` — **legacy Streamlit (562 LOC, en cours de retrait, mypy tolérant)**. Ne pas
  étendre ; le produit vit dans `src/studio/api` + `frontend/`.

Frontend (`frontend/`, React/TS/Vite/Tailwind, ~10k LOC) — surface de **revue** de briques
(`src/components/editor/`, `src/pages/`). Rendu vidéo Remotion : `render/`.
Tests (`tests/`, ~3,9k LOC) — golden tests + split cheap/`--runheavy` (cf. `conftest.py`).
Scripts/legacy : `scripts/` (`compiler.py`, `generate_assets.py`).

## Commandes

```bash
# Boucle de vérif complète (Docker dev) — mypy cliquet (baseline 0) + pytest + build front
make verify
make e2e            # tests navigateur Playwright (front en mock)

# Chemin natif (sans Docker, p.ex. conteneur web) :
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q            # tests rapides (~6 s) ; --runheavy pour tout
python -m mypy src             # type-check
# Front : cd frontend && npm install && npm run build
```

## Conventions (non déductibles du code)

- Prompts visuels en **anglais** ; dialogues/narration en **français**.
- Noms de personnages = **prénoms humains français** (jamais « Monster A »).
- Les prompts vidéo imposent une **caméra statique stricte** (évite le drift du modèle).
- Backend : respecter les **ports** (`ports.py`) et l'**immutabilité** de l'IR `VideoSpec` ;
  **idempotence** de génération (un asset `ready` n'est ni régénéré ni repayé).
- Zones **mypy strict** : `src.infra.*`, `src.features.*`, `src.studio.db.*` (cf. `pyproject.toml`).
