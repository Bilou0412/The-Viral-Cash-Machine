# 🚀 ViralCashMachine (VCM Studio)

**Créateur de vidéos verticales 9:16** pour TikTok / YouTube Shorts / Instagram Reels.
L'IA **écrit et découpe** une idée en scènes puis en **briques éditables**, on **révise les
briques** dans une UI React, et on **ne régénère que ce qu'on touche** (maîtrise du coût).

> Dialogues/narration en **français**, prompts visuels en **anglais**.
> Produit = FastAPI (API) + React/Vite (front) + rendu MoviePy/Remotion. *(L'ancien monolithe
> Streamlit a été retiré ; il est archivé sur la branche `master`.)*

## Le rail (pipeline unique)

```
idée (page « Créer »)
  → décomposeur de scènes (Fake offline / OpenAI 2 phases)   → VideoPlan
  → scene_plan_to_document                                    → EditorDocument v5 (briques + scènes)
  → UI de revue React (timeline multipiste, régénération ciblée)
  → document_to_spec                                          → VideoSpec (IR immuable)
  → resolve_real + MoviePyRenderEngine                        → MP4 final
```

Chaque **FORMAT** (« moule » : CYOA horreur #1, scènes libres #2…) produit le **même**
`EditorDocument` v5 — un seul rail, cf. `.claude/rules/architecture.md`.

## 🐳 Démarrage rapide (Docker)

```bash
cp .env.example .env      # puis renseigner OPENAI_API_KEY + REPLICATE_API_TOKEN
docker compose up --build
```

Ouvrir **http://localhost:8000**. DB (SQLite) et assets sont persistés sur l'hôte dans
`./studio_data/`. L'image build le front React, le package Remotion et sert le tout via FastAPI.

## 💻 Développement natif (sans Docker)

```bash
# Backend (API FastAPI)
pip install -r requirements.txt -r requirements-dev.txt
python -m uvicorn src.studio.api.app:app --reload --port 8000

# Frontend (Vite dev server, proxy vers l'API)
cd frontend && npm install && npm run dev        # http://localhost:5173
```

## ✅ Vérification

```bash
python -m pytest -q            # tests rapides (~6 s ; --runheavy pour tout)
python -m mypy src             # type-check strict (cliquet baseline 0)
cd frontend && npm run build   # tsc + vite
# Boucle complète : bash scripts/verify.sh [--heavy|--e2e]  (ou `make verify` en Docker)
```

## 🔑 Configuration

Clés dans `.env` (voir `.env.example` pour la liste complète : DB Postgres, stockage R2, CORS,
`VCM_RENDER_BASE`) :

| Variable | Rôle |
|---|---|
| `OPENAI_API_KEY` | GPT réel (décomposition, agents). Absent → impls **Fake** offline. |
| `REPLICATE_API_TOKEN` | Génération image/vidéo/voix (Replicate). |
| `VCM_OUTPUT_DIR` | Dossier des assets (défaut `exports/`). |

## 📂 Structure

```text
src/
├── features/        # features à ports (scenes, scripting, formats, crew, crew_room,
│                    #   virality, performance, publish, storage, assets, compositing…)
├── editor/          # ClipBrick v5, compile_shot (prompts), describe, document_to_spec
├── videospec/       # IR VideoSpec + rendu MoviePy + resolvers
├── studio/api/      # backend FastAPI (routes, services, db sqlmodel)
└── infra/           # download, logging
frontend/            # React/TS/Vite/Tailwind — surface de revue des briques
render/              # composition Remotion (rendu MP4 server-side)
tests/               # golden + suite cheap/heavy
scripts/             # dogfood_editor.py, compiler.py, generate_assets.py
```

## 📖 Documentation

- **`ROADMAP.md`** — source unique de vérité (état + étapes ; `/resume` démarre ici).
- **`CLAUDE.md`** — carte du code + conventions.
- **`.claude/rules/architecture.md`** — la loi du « rail unique ».
- **`docs/`** — `DECISIONS.md`, `GTM.md`, `DEPLOY.md` (runbook Fly.io), `AUDIT-2026-07.md`.
