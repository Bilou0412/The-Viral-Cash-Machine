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
    EditorDocRepo,
    EpisodeRepo,
    ProjectRepo,
    ScriptRepo,
)
from . import settings
from .events import bus
from .services.editor_generation import (
    EditorGenerationService,
    regenerate_brick,
)
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
    allow_origins=settings.cors_origins(),
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


def get_catalog_client() -> Any:
    """Provide the Replicate model-catalog client (overridden with a fake in tests)."""
    from .services.model_catalog import ReplicateCatalogClient

    return ReplicateCatalogClient()


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
    theme: str = "horror"             # DA / thème de l'épisode


class ScriptGenIn(BaseModel):
    prompt: str                       # l'aventure (thème/pitch) — requis
    char_left_name: str = "Étienne"
    char_right_name: str = "Marc"
    char_left_desc: str = ""          # description optionnelle du créateur
    char_right_desc: str = ""
    n_rounds: int = 3                 # nombre de séquences-choix (1..8)


class ScriptEditIn(BaseModel):
    script_json: str


class AssetUpdateIn(BaseModel):
    """Édition d'un asset depuis la revue (M1) : prompt et/ou écarté."""

    prompt: Optional[str] = None
    excluded: Optional[bool] = None


class EditorDocIn(BaseModel):
    """Création d'un document de l'éditeur timeline (E5)."""

    project_id: int
    title: str = "Sans titre"


class EditorDocSaveIn(BaseModel):
    """Sauvegarde d'un document : le doc d'autoring (+ titre optionnel)."""

    title: Optional[str] = None
    doc: dict[str, Any]


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
        body.project_id, body.title, draft_mode=body.draft_mode, theme=body.theme
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
# Themes (DA) — pour le sélecteur du wizard
# ---------------------------------------------------------------------------


@app.get("/api/themes")
def list_themes_route() -> list[dict[str, str]]:
    """Thèmes (DA) disponibles : [{name, label}, ...]."""
    from ...features.scripting.themes import list_themes

    return list_themes()


# ---------------------------------------------------------------------------
# Éditeur — catalogue de briques & modèles (inspecteur dynamique, E4)
# ---------------------------------------------------------------------------


@app.get("/api/bricks")
def list_bricks_route() -> list[dict[str, Any]]:
    """Briques génératives : contrat (champs requis) + 3 modèles préférés."""
    from ...features.compositing.registry import CONTRACTS

    return [
        {
            "kind": c.kind,
            "required_fields": [f.name for f in c.fields if f.required],
            "preferred_models": list(c.preferred_models),
        }
        for c in CONTRACTS.values()
    ]


@app.get("/api/models/search")
def model_search_route(
    kind: str, q: str = "", client: Any = Depends(get_catalog_client)
) -> list[Any]:
    """Modèles satisfaisant le contrat de la brique `kind` et la requête `q`."""
    from .services.model_catalog import search_models

    try:
        return search_models(kind, q, client)
    except KeyError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/models/{owner}/{name}/form")
def model_form_route(
    owner: str, name: str, client: Any = Depends(get_catalog_client)
) -> Any:
    """Descripteur de formulaire (tous les arguments du modèle) pour l'inspecteur."""
    from .services.model_catalog import form_descriptor

    try:
        return form_descriptor(f"{owner}/{name}", client)
    except Exception as exc:
        raise HTTPException(502, f"impossible de lire le schéma du modèle: {exc}")


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
        body.char_left_desc, body.char_right_desc, n_rounds=body.n_rounds,
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


@app.patch("/api/assets/{asset_id}")
def update_asset(
    asset_id: int, body: AssetUpdateIn, session: Session = Depends(_session)
) -> Asset:
    """Revue M1 : éditer le prompt d'un asset et/ou l'écarter du montage."""
    asset = AssetRepo(session).update(
        asset_id, prompt=body.prompt, excluded=body.excluded
    )
    if asset is None:
        raise HTTPException(404, f"asset {asset_id} not found")
    return asset


# ---------------------------------------------------------------------------
# Montage + library
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/montage")
def montage_episode(
    episode_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Lance le montage HORS du cycle requête (MoviePy = plusieurs minutes).

    Sync : valide l'épisode + les prérequis (409 si pas d'assets vidéo prêts).
    Puis planifie `assemble_rich` en tâche de fond ; le client suit l'avancement
    via SSE /api/events/{id} et récupère le résultat sur /api/episodes/{id}/video.
    (Un montage synchrone dépasserait le timeout proxy ~60s en prod.)
    """
    _require_episode(session, episode_id)
    svc = MontageService(engine)
    if not svc.has_renderable_inputs(episode_id):
        raise HTTPException(409, f"episode {episode_id} has no ready video assets to assemble")
    background.add_task(svc.assemble_rich, episode_id)
    return {"episode_id": episode_id, "status": "scheduled"}


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
# Éditeur timeline — documents, génération, render-model (E5)
# ---------------------------------------------------------------------------


def _require_editor_doc(session: Session, doc_id: int) -> Any:
    row = EditorDocRepo(session).get(doc_id)
    if row is None:
        raise HTTPException(404, f"editor document {doc_id} not found")
    return row


@app.get("/api/editor/documents")
def list_editor_documents(
    project_id: Optional[int] = None, session: Session = Depends(_session)
) -> list[dict[str, Any]]:
    repo = EditorDocRepo(session)
    rows = repo.by_project(project_id) if project_id is not None else repo.list()
    return [
        {"id": r.id, "project_id": r.project_id, "title": r.title} for r in rows
    ]


@app.post("/api/editor/documents")
def create_editor_document(
    body: EditorDocIn, session: Session = Depends(_session)
) -> dict[str, Any]:
    if ProjectRepo(session).get(body.project_id) is None:
        raise HTTPException(404, f"project {body.project_id} not found")
    from ...editor.document import EditorDocument

    doc = EditorDocument(title=body.title)
    row = EditorDocRepo(session).create(
        body.project_id, body.title, doc.model_dump_json()
    )
    return {
        "id": row.id,
        "project_id": row.project_id,
        "title": row.title,
        "doc": json.loads(row.doc_json),
    }


@app.post("/api/episodes/{episode_id}/editor-document")
def create_editor_document_from_script(
    episode_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    """Matérialise le script de l'épisode en document de briques ÉDITABLE (R1).

    C'est le chaînon « l'IA écrit → je révise en briques » : on lit le script
    (`AdventureScript`), on le transforme en arbre `ClipBrick` via
    `adventure_to_document`, et on persiste le document pour la revue/édition.
    """
    episode = _require_episode(session, episode_id)
    script = _load_script(session, episode_id)
    from ...features.scripting.adventure_to_bricks import adventure_to_document

    doc = adventure_to_document(script, title=f"Épisode {episode_id}")
    row = EditorDocRepo(session).create(
        episode.project_id,
        doc.title,
        doc.model_dump_json(),
        episode_id=episode_id,
        schema_version=doc.schema_version,
    )
    return {
        "id": row.id,
        "project_id": row.project_id,
        "episode_id": row.episode_id,
        "title": row.title,
        "doc": json.loads(row.doc_json),
    }


@app.get("/api/editor/documents/{doc_id}")
def get_editor_document(
    doc_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    row = _require_editor_doc(session, doc_id)
    from ...editor import upgrade_document

    doc = upgrade_document(json.loads(row.doc_json))
    return {
        "id": row.id,
        "project_id": row.project_id,
        "title": row.title,
        "doc": json.loads(doc.model_dump_json()),
    }


@app.put("/api/editor/documents/{doc_id}")
def save_editor_document(
    doc_id: int, body: EditorDocSaveIn, session: Session = Depends(_session)
) -> dict[str, Any]:
    _require_editor_doc(session, doc_id)
    from ...editor.document import EditorDocument

    try:
        doc = EditorDocument.model_validate(body.doc)
    except Exception as exc:
        raise HTTPException(422, f"invalid EditorDocument: {exc}")
    row = EditorDocRepo(session).save(
        doc_id, doc.model_dump_json(), title=body.title
    )
    assert row is not None  # existence checked above
    return {
        "id": row.id,
        "project_id": row.project_id,
        "title": row.title,
        "doc": json.loads(row.doc_json),
    }


@app.post("/api/editor/documents/{doc_id}/generate")
def generate_editor_document(
    doc_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
    provider: Optional[AssetProvider] = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_editor_doc(session, doc_id)
    service = EditorGenerationService(
        engine, provider=provider, downloader=downloader
    )
    background.add_task(service.generate_document, doc_id)
    return {"id": doc_id, "status": "scheduled"}


@app.post("/api/editor/documents/{doc_id}/bricks/{brick_id}/regenerate")
def regenerate_editor_brick(
    doc_id: int,
    brick_id: str,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
    provider: Optional[AssetProvider] = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_editor_doc(session, doc_id)
    background.add_task(
        regenerate_brick, engine, doc_id, brick_id, provider, downloader
    )
    return {"id": doc_id, "brick_id": brick_id, "status": "scheduled"}


@app.get("/api/editor/documents/{doc_id}/render-model")
def editor_render_model(
    doc_id: int, session: Session = Depends(_session)
) -> dict[str, Any]:
    row = _require_editor_doc(session, doc_id)
    from ...editor import upgrade_document
    from ...editor.resolve import resolve

    doc = upgrade_document(json.loads(row.doc_json))
    asset_src = {
        a.beat: f"/api/assets/{a.id}/file"
        for a in AssetRepo(session).assets_by_document(doc_id)
        if a.status == "ready" and not a.excluded
    }
    model = resolve(doc, asset_src)
    return json.loads(model.model_dump_json())


@app.post("/api/editor/documents/{doc_id}/render")
def render_editor_document(
    doc_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Export MP4 via Remotion (subprocess Node) — planifié en tâche de fond."""
    _require_editor_doc(session, doc_id)
    from .services.remotion_render import render_document

    background.add_task(render_document, engine, doc_id)
    return {"id": doc_id, "status": "scheduled"}


@app.get("/api/editor/documents/{doc_id}/video")
def editor_document_video(
    doc_id: int, session: Session = Depends(_session)
) -> FileResponse:
    """Sert le MP4 final d'un document éditeur (rendu Remotion)."""
    row = _require_editor_doc(session, doc_id)
    project = ProjectRepo(session).get(row.project_id)
    project_name = project.name if project else f"project_{row.project_id}"
    from .services.paths import editor_dir

    path = os.path.join(editor_dir(project_name, doc_id), "final_video.mp4")
    if not os.path.exists(path):
        raise HTTPException(404, "final video not available")
    return FileResponse(path)


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
