"""VCM Studio FastAPI application (phase U1).

Sits on top of the existing Aventure brain (pipeline / features) and the U0 DB
layer. Exposes the route contract the React studio aligns on.

Run locally:
    .venv/bin/uvicorn src.studio.api.app:app --reload

Test env knobs:
    VCM_STUDIO_DB=sqlite:///:memory:   # isolated DB
    (no OPENAI_API_KEY)                 # script generation uses the Fake decomposer

Asset generation and montage default to the real Replicate/MoviePy backends; the
TestClient suite injects fakes via the dependency overrides below, so the test
suite never touches the network or FFmpeg.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlmodel import Session

from ...features.assets.ports import AssetProvider
from ..db.engine import get_engine, init_db
from ..db.models import Asset, Episode, Project
from ..db.repositories import (
    AssetRepo,
    CostRepo,
    EpisodeRepo,
    ProjectRepo,
    ScriptRepo,
)
from .events import bus
from .services.generation import AssetGenerationService, regenerate_asset
from .services.generation_plan import estimate_cost, plan_episode_assets
from .services.montage import MontageService
from .services.scripting import generate_script

if TYPE_CHECKING:
    from ...features.scripting.adventure import AdventureScript

# ---------------------------------------------------------------------------
# App + dependency wiring (overridable in tests)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db(get_engine())
    yield


app = FastAPI(title="VCM Studio API", version="1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_engine() -> Engine:
    """Provide the shared engine. Overridden in tests with a tmp/in-memory one."""
    return get_engine()


def get_asset_provider() -> Optional[AssetProvider]:
    """Provide the asset provider. None -> service builds the real Replicate one."""
    return None


def get_downloader() -> Any:
    """Provide the asset downloader. None -> service uses the real HTTP download."""
    return None


def _session(engine: Engine = Depends(get_db_engine)) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ProjectIn(BaseModel):
    name: str
    settings_json: Optional[str] = None


class EpisodeIn(BaseModel):
    project_id: int
    title: str
    draft_mode: bool = True


class ScriptGenIn(BaseModel):
    prompt: str                       # l'aventure (thème/pitch) — requis
    char_left_name: str = "Étienne"
    char_right_name: str = "Marc"
    char_left_desc: str = ""          # description optionnelle du créateur
    char_right_desc: str = ""


class ScriptEditIn(BaseModel):
    script_json: str


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@app.get("/api/projects")
def list_projects(session: Session = Depends(_session)) -> list[Project]:
    return list(ProjectRepo(session).list())


@app.post("/api/projects")
def create_project(
    body: ProjectIn, session: Session = Depends(_session)
) -> Project:
    return ProjectRepo(session).create(body.name, body.settings_json)


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------


@app.get("/api/episodes")
def list_episodes(
    project_id: Optional[int] = None, session: Session = Depends(_session)
) -> list[Episode]:
    repo = EpisodeRepo(session)
    if project_id is not None:
        return list(repo.by_project(project_id))
    return list(repo.list())


@app.post("/api/episodes")
def create_episode(
    body: EpisodeIn, session: Session = Depends(_session)
) -> Episode:
    if ProjectRepo(session).get(body.project_id) is None:
        raise HTTPException(404, f"project {body.project_id} not found")
    return EpisodeRepo(session).create(
        body.project_id, body.title, draft_mode=body.draft_mode
    )


def _require_episode(session: Session, episode_id: int) -> Episode:
    episode = EpisodeRepo(session).get(episode_id)
    if episode is None:
        raise HTTPException(404, f"episode {episode_id} not found")
    return episode


@app.get("/api/episodes/{episode_id}")
def get_episode(
    episode_id: int, session: Session = Depends(_session)
) -> Episode:
    return _require_episode(session, episode_id)


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/script")
def generate_episode_script(
    episode_id: int, body: ScriptGenIn, session: Session = Depends(_session)
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    script = generate_script(
        body.prompt, body.char_left_name, body.char_right_name,
        body.char_left_desc, body.char_right_desc,
    )
    ScriptRepo(session).create(episode_id, script.model_dump_json())
    data: dict[str, Any] = json.loads(script.model_dump_json())
    return data


@app.get("/api/episodes/{episode_id}/script")
def get_episode_script(
    episode_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    row = ScriptRepo(session).latest_for_episode(episode_id)
    if row is None:
        raise HTTPException(404, "no script yet for this episode")
    data: dict[str, Any] = json.loads(row.script_json)
    return data


@app.put("/api/episodes/{episode_id}/script")
def edit_episode_script(
    episode_id: int, body: ScriptEditIn, session: Session = Depends(_session)
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    # Validate the edit against the schema before persisting.
    from ...features.scripting.adventure import AdventureScript

    try:
        script = AdventureScript.model_validate_json(body.script_json)
    except Exception as exc:
        raise HTTPException(422, f"invalid AdventureScript: {exc}")
    row = ScriptRepo(session).create(
        episode_id, script.model_dump_json(), edited=True
    )
    data: dict[str, Any] = json.loads(row.script_json)
    return data


# ---------------------------------------------------------------------------
# Beats (prompts) + cost estimate
# ---------------------------------------------------------------------------


def _load_script(session: Session, episode_id: int) -> "AdventureScript":
    from ...features.scripting.adventure import AdventureScript

    row = ScriptRepo(session).latest_for_episode(episode_id)
    if row is None:
        raise HTTPException(404, "no script yet for this episode")
    return AdventureScript.model_validate_json(row.script_json)


@app.get("/api/episodes/{episode_id}/beats")
def get_episode_beats(
    episode_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    script = _load_script(session, episode_id)
    plan = plan_episode_assets(script)
    return {
        "episode_id": episode_id,
        "assets": [
            {
                "round_index": a.round_index,
                "beat": a.beat,
                "kind": a.kind,
                "image_prompt": a.image_prompt,
                "motion_prompt": a.motion_prompt,
                "text": a.text,
            }
            for a in plan
        ],
    }


@app.get("/api/episodes/{episode_id}/cost")
def get_episode_cost(
    episode_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    episode = _require_episode(session, episode_id)
    script = _load_script(session, episode_id)
    est = estimate_cost(script, draft=episode.draft_mode)
    actual = CostRepo(session).cost_total_by_episode(episode_id)
    return {
        "episode_id": episode_id,
        "estimated_usd": est.total_usd,
        "actual_usd": round(actual, 4),
        "breakdown": [
            {
                "model": line.model,
                "units": line.units,
                "unit_kind": line.unit_kind,
                "amount_usd": line.amount_usd,
            }
            for line in est.lines
        ],
    }


# ---------------------------------------------------------------------------
# Asset generation
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/assets/generate")
def generate_assets(
    episode_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
    provider: Optional[AssetProvider] = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    script = _load_script(session, episode_id)
    service = AssetGenerationService(engine, provider=provider, downloader=downloader)
    background.add_task(service.generate_episode, episode_id, script)
    return {"episode_id": episode_id, "status": "scheduled"}


@app.post("/api/assets/{asset_id}/regenerate")
def regenerate_one_asset(
    asset_id: int,
    background: BackgroundTasks,
    engine: Engine = Depends(get_db_engine),
    provider: Optional[AssetProvider] = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    background.add_task(regenerate_asset, engine, asset_id, provider, downloader)
    return {"asset_id": asset_id, "status": "scheduled"}


@app.get("/api/episodes/{episode_id}/assets")
def list_episode_assets(
    episode_id: int, session: Session = Depends(_session)
) -> list[Asset]:
    _require_episode(session, episode_id)
    return list(AssetRepo(session).assets_by_episode(episode_id))


# ---------------------------------------------------------------------------
# Montage + library
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/montage")
def montage_episode(
    episode_id: int,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    _require_episode(session, episode_id)
    try:
        output_path = MontageService(engine).assemble_rich(episode_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return {"episode_id": episode_id, "final_path": output_path}


@app.post("/api/episodes/{episode_id}/produce")
def produce_full_episode(
    episode_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Un bouton = toute la vidéo : assets aventure + intro + montage (fond)."""
    _require_episode(session, episode_id)
    _load_script(session, episode_id)  # 404 si pas de script
    from .services.produce import produce_episode

    background.add_task(produce_episode, engine, episode_id)
    return {"episode_id": episode_id, "status": "scheduled"}


@app.get("/api/library")
def library(session: Session = Depends(_session)) -> list[dict[str, Any]]:
    episodes = EpisodeRepo(session).list()
    return [
        {
            "episode_id": e.id,
            "title": e.title,
            "project_id": e.project_id,
            "status": e.status,
            "duration_s": e.duration_s,
            "final_path": e.final_path,
        }
        for e in episodes
        if e.final_path
    ]


# ---------------------------------------------------------------------------
# SSE progress + file serving
# ---------------------------------------------------------------------------


@app.get("/api/events/{episode_id}")
async def episode_events(episode_id: int) -> StreamingResponse:
    queue = bus.subscribe(episode_id)

    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield bus.format_sse(event)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # SSE comment heartbeat
        finally:
            bus.unsubscribe(episode_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/assets/{asset_id}/file")
def asset_file(
    asset_id: int, session: Session = Depends(_session)
) -> FileResponse:
    asset = AssetRepo(session).get(asset_id)
    if asset is None or not asset.local_path or not os.path.exists(asset.local_path):
        raise HTTPException(404, "asset file not available")
    return FileResponse(asset.local_path)


@app.get("/api/episodes/{episode_id}/video")
def episode_video(
    episode_id: int, session: Session = Depends(_session)
) -> FileResponse:
    episode = _require_episode(session, episode_id)
    if not episode.final_path or not os.path.exists(episode.final_path):
        raise HTTPException(404, "final video not available")
    return FileResponse(episode.final_path)


# ---------------------------------------------------------------------------
# Front statique (SPA) — servi par FastAPI quand le build existe (Docker/prod).
# Monté APRÈS toutes les routes /api ; absent en tests (pas de build) → no-op.
# ---------------------------------------------------------------------------

_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend", "dist")
)
if os.path.isdir(_DIST):
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(_DIST, "assets")),
        name="spa-assets",
    )

    @app.get("/{full_path:path}")
    def _spa(full_path: str) -> FileResponse:
        """Sert le SPA : un fichier réel s'il existe, sinon index.html (routing client)."""
        candidate = os.path.join(_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_DIST, "index.html"))
