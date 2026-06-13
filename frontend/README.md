# VCM Studio — Frontend

React studio for the VCM Aventure pipeline (AI vertical 9:16 videos for
TikTok / Shorts / Reels). Dark, dense studio theme; 9:16 previews everywhere.

Stack: **Vite + React + TypeScript + Tailwind + shadcn-style UI** + React Query +
React Router + sonner (toasts).

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

By default (`.env.development`) the app talks to the **live U1 FastAPI backend**
(`VITE_USE_MOCKS=false`). Start it first:

```bash
# from repo root
.venv/bin/uvicorn src.studio.api.app:app --reload   # serves :8000 (U1)
```

For an offline demo with no backend, set `VITE_USE_MOCKS=true` — every call is
served by an in-memory mock that satisfies the same contract.

Vite proxies `/api/*` → `http://localhost:8000` (see `vite.config.ts`), so no
CORS or base-URL config is needed in the client.

> Note: there is no single-episode `GET /api/episodes/{id}` route in U1 yet, so
> `api.getEpisode(id)` resolves from `GET /api/episodes`. If that route is added,
> simplify it back to a direct fetch (see comment in `src/lib/api.ts`).

## Scripts

| Command         | Description                          |
|-----------------|--------------------------------------|
| `npm run dev`   | Dev server (HMR) on :5173            |
| `npm run build` | Type-check (`tsc -b`) + production build |
| `npm run lint`  | ESLint                               |
| `npm run preview` | Serve the production build          |

## Screens

| Route | Screen | What |
|---|---|---|
| `/` | Dashboard | Projects, recent episodes, status/duration/cost, cumulative cost |
| `/new` | New Episode wizard | Base prompt + character names → generates the script |
| `/episodes/:id` | Redirect | Routes to script/assets/montage by episode status |
| `/episodes/:id/script` | Script & Casting | Editable `AdventureScript` (3 rounds, choices, voices), save, regenerate |
| `/episodes/:id/assets` | Assets | Per-round beats: first frame (image) + video, per-unit regen, draft/final toggle, audio, cost-before-generate, SSE progress |
| `/episodes/:id/montage` | Montage & Preview | Assemble intro + rounds + epilogue, 9:16 player, download |
| `/library` | Library | Grid of final videos |

## Architecture

```
src/
├── lib/
│   ├── types.ts   # domain types mirroring the backend contract + AdventureScript
│   ├── api.ts     # typed API client (StudioApi); /api via Vite proxy; mock fallback
│   ├── mocks.ts   # contract-conformant in-memory backend (VITE_USE_MOCKS)
│   └── utils.ts   # cn(), formatters (cost/duration/date)
├── hooks/
│   ├── use-studio.ts      # React Query hooks + cache keys (qk) + mutations
│   └── use-job-events.ts  # SSE subscription for live job progress
├── components/
│   ├── ui/        # shadcn-style primitives (button, card, tabs, dialog, …)
│   └── studio/    # studio-specific (layout, vertical-preview, status-badge, states)
└── pages/         # one file per screen
```

The single source of truth for the API shape is `src/lib/api.ts` (`StudioApi`
type). When the U1 routes change, update `types.ts` + `api.ts` together; `mocks.ts`
must keep satisfying the same `StudioApi` type.

## Conventions

- All visual prompt fields are EN; dialogue/narration fields are FR (project rule).
  The script editor labels fields accordingly.
- Media (`<img>/<video>/<audio>`) fetch local files directly via
  `/api/assets/:id/file` and `/api/episodes/:id/video` (assets are downloaded to
  disk server-side; the client never touches perishable Replicate URLs).
