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

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from sqlmodel import Session
from starlette.middleware.sessions import SessionMiddleware

from ...features import storage
from ...features.assets.ports import AssetProvider
from ..db.engine import get_engine, init_db
from ..db.models import Asset, Episode, Project, User
from ..db.repositories import (
    AssetRepo,
    CostRepo,
    EditorDocRepo,
    EpisodeRepo,
    ProjectRepo,
    ScriptRepo,
    UserRepo,
)
from . import settings
from .events import bus
from .services.editor_generation import (
    EditorGenerationService,
    regenerate_brick,
)
from .services import auth, secrets
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
    eng = get_engine()
    init_db(eng)
    secrets.apply_to_env(eng)  # load BYOK keys (entered in the UI) into the env
    auth.bootstrap_admin(eng)  # crée l'admin depuis VCM_ADMIN_EMAIL/PASSWORD si posés
    yield


app = FastAPI(title="VCM Studio API", version="1.0", lifespan=_lifespan)

# --- Auth (Phase B.1) -------------------------------------------------------
# Le login verrouille TOUTE l'API : seules ces routes sont accessibles sans
# session. Les pages du SPA (chemins hors /api) restent publiques (elles doivent
# pouvoir charger /login).
_AUTH_EXEMPT = frozenset({"/api/auth/login", "/api/auth/register"})


def _session_secret() -> str:
    """Clé de signature des cookies de session (VCM_SESSION_SECRET en prod)."""
    return os.environ.get("VCM_SESSION_SECRET") or "dev-insecure-change-me"


def _cookie_secure() -> bool:
    """Cookie ``Secure`` (HTTPS-only). Activé en prod via VCM_COOKIE_SECURE=1 ;
    désactivé par défaut pour le local/CI en HTTP (sinon la session ne persiste pas).
    """
    return os.environ.get("VCM_COOKIE_SECURE", "0") == "1"


# Ordre d'AJOUT = ordre d'exécution inversé (le dernier ajouté est le plus
# externe). On veut : CORS → SessionMiddleware → garde d'auth → route, donc on
# ajoute la garde en premier, la session ensuite, CORS en dernier.
@app.middleware("http")
async def _require_session(request: Request, call_next: Any) -> Response:
    path = request.url.path
    if path.startswith("/api/") and path not in _AUTH_EXEMPT:
        if not request.session.get("user_id"):
            return JSONResponse({"detail": "authentification requise"}, status_code=401)
    response: Response = await call_next(request)
    return response


app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret(),
    session_cookie="vcm_session",
    https_only=_cookie_secure(),
    same_site="lax",
)

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


# --- Auth dependencies (Phase B.1) -----------------------------------------


def require_user(
    request: Request, engine: Engine = Depends(get_db_engine)
) -> User:
    """Charge l'utilisateur de la session (401 si absent/invalide)."""
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(401, "authentification requise")
    with Session(engine) as session:
        user = UserRepo(session).get(int(uid))
    if user is None:
        request.session.clear()
        raise HTTPException(401, "session invalide")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """Réserve la route à l'admin (B.1 : seul l'admin peut dépenser les clés)."""
    if not user.is_admin:
        raise HTTPException(403, "réservé à l'administrateur")
    return user


def _public_user(user: User) -> dict[str, Any]:
    """Vue publique d'un utilisateur (jamais le hash du mot de passe)."""
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}


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
# Auth (Phase B.1) — inscription / connexion / session
# ---------------------------------------------------------------------------


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/register")
def register(
    body: RegisterIn, request: Request, engine: Engine = Depends(get_db_engine)
) -> dict[str, Any]:
    """Crée un compte (non-admin) et ouvre la session.

    B.1 : un inscrit lambda peut se connecter mais **pas** générer (routes de
    génération réservées à l'admin) — l'inscription s'ouvre vraiment en B.2.
    """
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(422, "email invalide")
    if len(body.password) < 8:
        raise HTTPException(422, "mot de passe trop court (8 caractères minimum)")
    with Session(engine) as session:
        repo = UserRepo(session)
        if repo.get_by_email(email) is not None:
            raise HTTPException(409, "cet email est déjà utilisé")
        user = repo.create(email, auth.hash_password(body.password), is_admin=False)
    request.session["user_id"] = user.id
    return _public_user(user)


@app.post("/api/auth/login")
def login(
    body: LoginIn, request: Request, engine: Engine = Depends(get_db_engine)
) -> dict[str, Any]:
    """Vérifie les identifiants et ouvre la session (cookie signé)."""
    email = body.email.strip().lower()
    with Session(engine) as session:
        user = UserRepo(session).get_by_email(email)
    if user is None or not auth.verify_password(user.password_hash, body.password):
        raise HTTPException(401, "identifiants invalides")
    request.session["user_id"] = user.id
    return _public_user(user)


@app.post("/api/auth/logout")
def logout(request: Request) -> dict[str, bool]:
    """Ferme la session (vide le cookie)."""
    request.session.clear()
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(require_user)) -> dict[str, Any]:
    """L'utilisateur courant (401 si non connecté → le front sait qu'il faut login)."""
    return _public_user(user)


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
    episode_id: int,
    body: ScriptGenIn,
    session: Session = Depends(_session),
    _admin: User = Depends(require_admin),
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
    repo = CostRepo(session)
    nodes = repo.actual_by_episode(episode_id)
    actual = sum(n["amount_usd"] for n in nodes)
    return {
        "episode_id": episode_id,
        "estimated_usd": est.total_usd,        # pré-vol (avant génération)
        "actual_usd": round(actual, 4),        # somme des coûts RÉELS enregistrés
        "breakdown": [
            {
                "model": line.model,
                "units": line.units,
                "unit_kind": line.unit_kind,
                "amount_usd": line.amount_usd,
            }
            for line in est.lines
        ],
        # Coût réel par nœud (après génération) : montant + provenance.
        "nodes": nodes,
    }


# ---------------------------------------------------------------------------
# Réglages : clés API saisies dans l'app (BYOK). Jamais renvoyées en clair.
# ---------------------------------------------------------------------------

class KeysIn(BaseModel):
    openai: Optional[str] = None
    replicate: Optional[str] = None


@app.get("/api/settings/keys")
def get_keys(engine: Engine = Depends(get_db_engine)) -> dict[str, bool]:
    """Statut des clés (configurées ou non). Ne renvoie jamais la valeur."""
    return secrets.keys_status(engine)


@app.put("/api/settings/keys")
def put_keys(
    body: KeysIn,
    engine: Engine = Depends(get_db_engine),
    _admin: User = Depends(require_admin),
) -> dict[str, bool]:
    """Enregistre les clés non vides (DB + os.environ) et renvoie le statut."""
    secrets.set_keys(engine, openai=body.openai, replicate=body.replicate)
    return secrets.keys_status(engine)


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
    _admin: User = Depends(require_admin),
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
    _admin: User = Depends(require_admin),
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
    _admin: User = Depends(require_admin),
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
    _admin: User = Depends(require_admin),
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
    _admin: User = Depends(require_admin),
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
) -> Response:
    asset = AssetRepo(session).get(asset_id)
    if asset is None or not asset.local_path or not storage.exists(asset.local_path):
        raise HTTPException(404, "asset file not available")
    return storage.serve(asset.local_path)


@app.get("/api/episodes/{episode_id}/video")
def episode_video(
    episode_id: int, session: Session = Depends(_session)
) -> Response:
    episode = _require_episode(session, episode_id)
    if not episode.final_path or not storage.exists(episode.final_path):
        raise HTTPException(404, "final video not available")
    return storage.serve(episode.final_path)


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
