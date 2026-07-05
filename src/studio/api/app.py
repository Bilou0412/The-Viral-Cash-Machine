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
import re
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Literal

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
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
from ..db.models import Asset, Episode, Project, PromptTemplate, Template, User
from ..db.repositories import (
    AssetRepo,
    CostRepo,
    EditorDocRepo,
    EpisodeRepo,
    ProjectRepo,
    PromptTemplateRepo,
    ScriptRepo,
    TemplateRepo,
    UserRepo,
)
from . import settings
from .events import bus
from .services import auth, secrets
from .services.editor_generation import (
    EditorGenerationService,
    regenerate_brick,
)
from .services.generation import AssetGenerationService, regenerate_asset
from .services.generation_plan import estimate_cost, plan_episode_assets
from .services.montage import MontageService
from .services.scenes import generate_video_plan
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
    if (
        path.startswith("/api/")
        and path not in _AUTH_EXEMPT
        and not request.session.get("user_id")
    ):
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


def get_asset_provider() -> AssetProvider | None:
    """Provide the asset provider. None -> service builds the real Replicate one."""
    return None


def get_downloader() -> Any:
    """Provide the asset downloader. None -> service uses the real HTTP download."""
    return None


def get_catalog_client(
    request: Request, engine: Engine = Depends(get_db_engine)
) -> Any:
    """Client catalogue Replicate scopé sur la clé de l'utilisateur courant (B.2).

    Overridé par un fake en test. Le middleware garantit une session sur /api/*,
    donc ``user_id`` est présent ; on lit sa clé Replicate (None si absente).
    """
    from .services.model_catalog import ReplicateCatalogClient

    uid = request.session.get("user_id")
    token = secrets.get_user_keys(engine, int(uid)).replicate if uid else None
    return ReplicateCatalogClient(api_token=token)


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


# --- Ownership (Phase B.2) — isolation des données par utilisateur -----------
# Cross-tenant → 404 (ne pas divulguer l'existence). L'admin bypasse tout.


def _uid(user: User) -> int:
    """id d'un utilisateur chargé (toujours défini) — typé int pour les repos."""
    assert user.id is not None
    return user.id


def _require_owned_project(
    session: Session, user: User, project_id: int
) -> Project:
    project = ProjectRepo(session).get(project_id)
    if project is None or (not user.is_admin and project.owner_id != user.id):
        raise HTTPException(404, f"project {project_id} not found")
    return project


def _require_owned_episode(
    session: Session, user: User, episode_id: int
) -> Episode:
    episode = EpisodeRepo(session).get(episode_id)
    if episode is None:
        raise HTTPException(404, f"episode {episode_id} not found")
    _require_owned_project(session, user, episode.project_id)  # 404 si pas owner
    return episode


def _require_owned_doc(session: Session, user: User, doc_id: int) -> Any:
    row = EditorDocRepo(session).get(doc_id)
    if row is None:
        raise HTTPException(404, f"editor document {doc_id} not found")
    _require_owned_project(session, user, row.project_id)
    return row


def _require_owned_template(
    session: Session, user: User, template_id: int
) -> Template:
    row = TemplateRepo(session).get(template_id)
    if row is None or (not user.is_admin and row.owner_id != user.id):
        raise HTTPException(404, f"template {template_id} not found")
    return row


def _require_owned_prompt_template(
    session: Session, user: User, template_id: int
) -> PromptTemplate:
    row = PromptTemplateRepo(session).get(template_id)
    if row is None or (not user.is_admin and row.owner_id != user.id):
        raise HTTPException(404, f"prompt template {template_id} not found")
    return row


def _require_owned_asset(session: Session, user: User, asset_id: int) -> Asset:
    asset = AssetRepo(session).get(asset_id)
    if asset is None:
        raise HTTPException(404, f"asset {asset_id} not found")
    # Les assets de l'éditeur ont episode_id=0 → passer par le document, sinon
    # par l'épisode.
    if asset.editor_document_id is not None:
        _require_owned_doc(session, user, asset.editor_document_id)
    else:
        _require_owned_episode(session, user, asset.episode_id)
    return asset


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ProjectIn(BaseModel):
    name: str
    settings_json: str | None = None


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

    prompt: str | None = None
    excluded: bool | None = None


class EditorDocIn(BaseModel):
    """Création d'un document de l'éditeur timeline (E5)."""

    project_id: int
    title: str = "Sans titre"


class EditorDocSaveIn(BaseModel):
    """Sauvegarde d'un document : le doc d'autoring (+ titre optionnel)."""

    title: str | None = None
    doc: dict[str, Any]


class SceneGenIn(BaseModel):
    """Créer une vidéo par scènes : l'idée (+ style optionnel + nb de scènes)."""

    prompt: str
    style_identity: str = ""
    n_scenes: int = 3
    title: str = "Nouvelle vidéo"


class TemplateSlotIn(BaseModel):
    """Un slot du template : le CONTENANT (structure), jamais le contenu."""

    id: str
    kind: Literal["video", "photo"]
    duration: float = 4.0
    aspect_ratio: str = "9:16"
    resolution: str = "720p"
    narration: bool = True


class TemplateIn(BaseModel):
    """Création d'un template (bibliothèque de structures réutilisables)."""

    name: str = "Nouveau template"
    slots: list[TemplateSlotIn] = []


class TemplateSaveIn(BaseModel):
    """Sauvegarde d'un template : ses slots (+ nom optionnel)."""

    name: str | None = None
    slots: list[TemplateSlotIn]


class RolePromptIn(BaseModel):
    """Un rôle/brique : le découpage à champs (le « cahier des charges »).

    ``fields`` mappe une clé du schéma de plan (décor, sujet, cadrage, action,
    caméra, narration, dialogue…) → texte à trous. Stockage volontairement
    générique pour étendre le schéma sans migration.
    """

    id: str
    label: str = ""
    fields: dict[str, str] = {}


class PromptTemplateIn(BaseModel):
    """Création d'un template de prompt système (identité + rôles à trous)."""

    name: str = "Nouveau style"
    identity: str = ""
    roles: list[RolePromptIn] = []


class PromptTemplateSaveIn(BaseModel):
    """Sauvegarde d'un template de prompt système."""

    name: str | None = None
    identity: str = ""
    roles: list[RolePromptIn] = []


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

    B.2 : chaque utilisateur ne voit que ses données et génère avec **ses**
    propres clés (chiffrées) — l'inscription est ouverte.
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
def list_projects(session: Session = Depends(_session),
    user: User = Depends(require_user)) -> list[Project]:
    repo = ProjectRepo(session)
    if user.is_admin:
        return list(repo.list())
    return list(repo.list_for_owner(_uid(user)))


@app.post("/api/projects")
def create_project(
    body: ProjectIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Project:
    return ProjectRepo(session).create(
        body.name, body.settings_json, owner_id=_uid(user)
    )


# ---------------------------------------------------------------------------
# Episodes
# ---------------------------------------------------------------------------


@app.get("/api/episodes")
def list_episodes(
    project_id: int | None = None, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> list[Episode]:
    repo = EpisodeRepo(session)
    if project_id is not None:
        _require_owned_project(session, user, project_id)  # 404 si pas owner
        return list(repo.by_project(project_id))
    if user.is_admin:
        return list(repo.list())
    return list(repo.by_owner(_uid(user)))


@app.post("/api/episodes")
def create_episode(
    body: EpisodeIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Episode:
    _require_owned_project(session, user, body.project_id)
    return EpisodeRepo(session).create(
        body.project_id, body.title, draft_mode=body.draft_mode, theme=body.theme
    )


@app.get("/api/episodes/{episode_id}")
def get_episode(
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Episode:
    return _require_owned_episode(session, user, episode_id)


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
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/models/{owner}/{name}/form")
def model_form_route(
    owner: str,
    name: str,
    kind: str | None = None,
    client: Any = Depends(get_catalog_client),
) -> Any:
    """Descripteur de formulaire (tous les arguments du modèle) pour l'inspecteur.

    ``kind`` (image/video/voice) attache un libellé métier FR à chaque input.
    """
    from .services.model_catalog import form_descriptor

    try:
        return form_descriptor(f"{owner}/{name}", client, kind=kind)
    except Exception as exc:
        raise HTTPException(502, f"impossible de lire le schéma du modèle: {exc}") from exc


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/script")
def generate_episode_script(
    episode_id: int,
    body: ScriptGenIn,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    _require_owned_episode(session, user, episode_id)
    # B.2 : script écrit avec la clé OpenAI de l'utilisateur (sinon décomposeur Fake).
    keys = secrets.get_user_keys(engine, _uid(user))
    script = generate_script(
        body.prompt, body.char_left_name, body.char_right_name,
        body.char_left_desc, body.char_right_desc, n_rounds=body.n_rounds,
        openai_key=keys.openai,
    )
    ScriptRepo(session).create(episode_id, script.model_dump_json())
    data: dict[str, Any] = json.loads(script.model_dump_json())
    return data


@app.get("/api/episodes/{episode_id}/script")
def get_episode_script(
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_episode(session, user, episode_id)
    row = ScriptRepo(session).latest_for_episode(episode_id)
    if row is None:
        raise HTTPException(404, "no script yet for this episode")
    data: dict[str, Any] = json.loads(row.script_json)
    return data


@app.put("/api/episodes/{episode_id}/script")
def edit_episode_script(
    episode_id: int, body: ScriptEditIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_episode(session, user, episode_id)
    # Validate the edit against the schema before persisting.
    from ...features.scripting.adventure import AdventureScript

    try:
        script = AdventureScript.model_validate_json(body.script_json)
    except Exception as exc:
        raise HTTPException(422, f"invalid AdventureScript: {exc}") from exc
    row = ScriptRepo(session).create(
        episode_id, script.model_dump_json(), edited=True
    )
    data: dict[str, Any] = json.loads(row.script_json)
    return data


# ---------------------------------------------------------------------------
# Beats (prompts) + cost estimate
# ---------------------------------------------------------------------------


def _load_script(session: Session, episode_id: int) -> AdventureScript:
    from ...features.scripting.adventure import AdventureScript

    row = ScriptRepo(session).latest_for_episode(episode_id)
    if row is None:
        raise HTTPException(404, "no script yet for this episode")
    return AdventureScript.model_validate_json(row.script_json)


@app.get("/api/episodes/{episode_id}/beats")
def get_episode_beats(
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_episode(session, user, episode_id)
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
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    episode = _require_owned_episode(session, user, episode_id)
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
    openai: str | None = None
    replicate: str | None = None


@app.get("/api/settings/keys")
def get_keys(
    engine: Engine = Depends(get_db_engine),
    user: User = Depends(require_user),
) -> dict[str, bool]:
    """Statut des clés de l'utilisateur courant. Ne renvoie jamais la valeur."""
    return secrets.keys_status(engine, _uid(user))


@app.put("/api/settings/keys")
def put_keys(
    body: KeysIn,
    engine: Engine = Depends(get_db_engine),
    user: User = Depends(require_user),
) -> dict[str, bool]:
    """Enregistre (chiffrées) les clés non vides de l'utilisateur et renvoie le statut."""
    secrets.set_keys(
        engine, _uid(user), openai=body.openai, replicate=body.replicate
    )
    return secrets.keys_status(engine, _uid(user))


# ---------------------------------------------------------------------------
# Uploads (Phase 3) — photos de l'utilisateur pour les inputs image des modèles
# ---------------------------------------------------------------------------


@app.post("/api/uploads")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
) -> dict[str, str]:
    """Stocke une photo uploadée (par-utilisateur) → renvoie sa ``ref`` de stockage.

    La ref sert de valeur d'input image dans une brique ; à la génération elle est
    poussée vers Replicate (Files API), comme le chaînage d'images généré.
    """
    import tempfile
    from uuid import uuid4

    data = await file.read()
    if not data:
        raise HTTPException(422, "fichier vide")
    if len(data) > 25_000_000:
        raise HTTPException(413, "fichier trop volumineux (max 25 Mo)")
    suffix = os.path.splitext(file.filename or "upload")[1][:12] or ".bin"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        ref = storage.persist_file(
            tmp_path, f"uploads/{_uid(user)}", f"{uuid4().hex}{suffix}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return {"ref": ref}


# ---------------------------------------------------------------------------
# Asset generation
# ---------------------------------------------------------------------------


@app.post("/api/episodes/{episode_id}/assets/generate")
def generate_assets(
    episode_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
    provider: AssetProvider | None = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_owned_episode(session, user, episode_id)
    script = _load_script(session, episode_id)
    keys = secrets.get_user_keys(engine, _uid(user))
    if provider is None and not keys.replicate:
        raise HTTPException(409, "ajoute tes clés Replicate dans Réglages pour générer")
    service = AssetGenerationService(
        engine,
        provider=provider,
        downloader=downloader,
        replicate_token=keys.replicate,
        openai_key=keys.openai,
    )
    background.add_task(service.generate_episode, episode_id, script)
    return {"episode_id": episode_id, "status": "scheduled"}


@app.post("/api/assets/{asset_id}/regenerate")
def regenerate_one_asset(
    asset_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
    provider: AssetProvider | None = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_owned_asset(session, user, asset_id)
    keys = secrets.get_user_keys(engine, _uid(user))
    if provider is None and not keys.replicate:
        raise HTTPException(409, "ajoute tes clés Replicate dans Réglages pour générer")
    background.add_task(
        regenerate_asset, engine, asset_id, provider, downloader,
        keys.replicate, keys.openai,
    )
    return {"asset_id": asset_id, "status": "scheduled"}


@app.get("/api/episodes/{episode_id}/assets")
def list_episode_assets(
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> list[Asset]:
    _require_owned_episode(session, user, episode_id)
    return list(AssetRepo(session).assets_by_episode(episode_id))


@app.patch("/api/assets/{asset_id}")
def update_asset(
    asset_id: int, body: AssetUpdateIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Asset:
    """Revue M1 : éditer le prompt d'un asset et/ou l'écarter du montage."""
    _require_owned_asset(session, user, asset_id)
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
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Lance le montage HORS du cycle requête (MoviePy = plusieurs minutes).

    Sync : valide l'épisode + les prérequis (409 si pas d'assets vidéo prêts).
    Puis planifie `assemble_rich` en tâche de fond ; le client suit l'avancement
    via SSE /api/events/{id} et récupère le résultat sur /api/episodes/{id}/video.
    (Un montage synchrone dépasserait le timeout proxy ~60s en prod.)
    """
    _require_owned_episode(session, user, episode_id)
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
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Un bouton = toute la vidéo : assets aventure + intro + montage (fond)."""
    _require_owned_episode(session, user, episode_id)
    _load_script(session, episode_id)  # 404 si pas de script
    keys = secrets.get_user_keys(engine, _uid(user))
    if not keys.replicate:
        raise HTTPException(409, "ajoute tes clés Replicate dans Réglages pour générer")
    from .services.produce import produce_episode

    background.add_task(
        produce_episode, engine, episode_id, "left", keys.replicate, keys.openai
    )
    return {"episode_id": episode_id, "status": "scheduled"}


@app.get("/api/library")
def library(session: Session = Depends(_session),
    user: User = Depends(require_user)) -> list[dict[str, Any]]:
    repo = EpisodeRepo(session)
    episodes = repo.list() if user.is_admin else repo.by_owner(_uid(user))
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


@app.get("/api/editor/documents")
def list_editor_documents(
    project_id: int | None = None, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> list[dict[str, Any]]:
    repo = EditorDocRepo(session)
    if project_id is not None:
        _require_owned_project(session, user, project_id)  # 404 si pas owner
        rows: Any = repo.by_project(project_id)
    elif user.is_admin:
        rows = repo.list()
    else:
        rows = repo.by_owner(_uid(user))
    return [
        {"id": r.id, "project_id": r.project_id, "title": r.title} for r in rows
    ]


@app.post("/api/editor/documents")
def create_editor_document(
    body: EditorDocIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_project(session, user, body.project_id)
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
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    """Matérialise le script de l'épisode en document de briques ÉDITABLE (R1).

    C'est le chaînon « l'IA écrit → je révise en briques » : on lit le script
    (`AdventureScript`), on le transforme en arbre `ClipBrick` via
    `adventure_to_document`, et on persiste le document pour la revue/édition.
    """
    episode = _require_owned_episode(session, user, episode_id)
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


@app.post("/api/episodes/{episode_id}/scene-document")
def create_scene_document(
    episode_id: int, body: SceneGenIn,
    session: Session = Depends(_session), user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Créateur de scènes : idée → l'IA découpe en scènes + plans courts → document
    de briques ÉDITABLE (index de scènes inclus), prêt pour la revue.

    Sans clé OpenAI → décrypteur Fake déterministe (offline). Photo-first : chaque
    scène porte une brique photo d'environnement (contexte figé) suivie de ses plans.
    """
    episode = _require_owned_episode(session, user, episode_id)
    keys = secrets.get_user_keys(engine, _uid(user))
    plan = generate_video_plan(
        body.prompt,
        style_identity=body.style_identity,
        n_scenes=body.n_scenes,
        openai_key=keys.openai,
    )
    from ...features.scenes import scene_plan_to_document

    doc = scene_plan_to_document(plan, title=body.title)
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
    doc_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    row = _require_owned_doc(session, user, doc_id)
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
    doc_id: int, body: EditorDocSaveIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_doc(session, user, doc_id)
    from ...editor.document import EditorDocument

    try:
        doc = EditorDocument.model_validate(body.doc)
    except Exception as exc:
        raise HTTPException(422, f"invalid EditorDocument: {exc}") from exc
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


# ---------------------------------------------------------------------------
# Templates (T1) — bibliothèque de structures réutilisables (le « contenant »)
# ---------------------------------------------------------------------------


def _template_dict(row: Template) -> dict[str, Any]:
    """Sérialise une ligne Template → { id, name, slots }."""
    data = json.loads(row.structure_json)
    slots = data.get("slots", []) if isinstance(data, dict) else []
    return {"id": row.id, "name": row.name, "slots": slots}


def _template_summary(row: Template) -> dict[str, Any]:
    data = json.loads(row.structure_json)
    slots = data.get("slots", []) if isinstance(data, dict) else []
    total = sum(float(s.get("duration", 0)) for s in slots)
    return {
        "id": row.id,
        "name": row.name,
        "slot_count": len(slots),
        "total_duration": total,
    }


@app.get("/api/templates")
def list_templates(
    session: Session = Depends(_session), user: User = Depends(require_user)
) -> list[dict[str, Any]]:
    repo = TemplateRepo(session)
    rows = repo.list() if user.is_admin else repo.list_for_owner(_uid(user))
    return [_template_summary(r) for r in rows]


@app.post("/api/templates")
def create_template(
    body: TemplateIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    structure = json.dumps({"slots": [s.model_dump() for s in body.slots]})
    row = TemplateRepo(session).create(body.name, structure, owner_id=_uid(user))
    return _template_dict(row)


@app.get("/api/templates/{template_id}")
def get_template(
    template_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    row = _require_owned_template(session, user, template_id)
    return _template_dict(row)


@app.put("/api/templates/{template_id}")
def save_template(
    template_id: int, body: TemplateSaveIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_template(session, user, template_id)
    structure = json.dumps({"slots": [s.model_dump() for s in body.slots]})
    row = TemplateRepo(session).save(template_id, structure, name=body.name)
    assert row is not None  # existence checked above
    return _template_dict(row)


@app.delete("/api/templates/{template_id}")
def delete_template(
    template_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, bool]:
    _require_owned_template(session, user, template_id)
    TemplateRepo(session).delete(template_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Templates de prompt système (T2.1) — l'identité + la trame à trous
# ---------------------------------------------------------------------------

_HOLE_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _holes_of(identity: str, roles: list[dict[str, Any]]) -> list[str]:
    """Trous ``{token}`` uniques (ordre d'apparition) : identité + champs des rôles."""
    seen: dict[str, None] = {}
    texts = [identity]
    for role in roles:
        fields = role.get("fields", {})
        if isinstance(fields, dict):
            texts.extend(str(v) for v in fields.values())
    for text in texts:
        for m in _HOLE_RE.findall(text):
            seen.setdefault(m, None)
    return list(seen)


def _prompt_template_dict(row: PromptTemplate) -> dict[str, Any]:
    roles = json.loads(row.roles_json)
    if not isinstance(roles, list):
        roles = []
    return {
        "id": row.id,
        "name": row.name,
        "identity": row.identity,
        "roles": roles,
        "holes": _holes_of(row.identity, roles),
    }


def _prompt_template_summary(row: PromptTemplate) -> dict[str, Any]:
    roles = json.loads(row.roles_json)
    if not isinstance(roles, list):
        roles = []
    return {
        "id": row.id,
        "name": row.name,
        "role_count": len(roles),
        "hole_count": len(_holes_of(row.identity, roles)),
    }


@app.get("/api/prompt-templates")
def list_prompt_templates(
    session: Session = Depends(_session), user: User = Depends(require_user)
) -> list[dict[str, Any]]:
    repo = PromptTemplateRepo(session)
    rows = repo.list() if user.is_admin else repo.list_for_owner(_uid(user))
    return [_prompt_template_summary(r) for r in rows]


@app.post("/api/prompt-templates")
def create_prompt_template(
    body: PromptTemplateIn, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    roles = json.dumps([r.model_dump() for r in body.roles])
    row = PromptTemplateRepo(session).create(
        body.name, body.identity, roles, owner_id=_uid(user)
    )
    return _prompt_template_dict(row)


@app.get("/api/prompt-templates/{template_id}")
def get_prompt_template(
    template_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    row = _require_owned_prompt_template(session, user, template_id)
    return _prompt_template_dict(row)


@app.put("/api/prompt-templates/{template_id}")
def save_prompt_template(
    template_id: int, body: PromptTemplateSaveIn,
    session: Session = Depends(_session), user: User = Depends(require_user)
) -> dict[str, Any]:
    _require_owned_prompt_template(session, user, template_id)
    roles = json.dumps([r.model_dump() for r in body.roles])
    row = PromptTemplateRepo(session).save(
        template_id, body.identity, roles, name=body.name
    )
    assert row is not None  # existence checked above
    return _prompt_template_dict(row)


@app.delete("/api/prompt-templates/{template_id}")
def delete_prompt_template(
    template_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, bool]:
    _require_owned_prompt_template(session, user, template_id)
    PromptTemplateRepo(session).delete(template_id)
    return {"ok": True}


@app.post("/api/editor/documents/{doc_id}/generate")
def generate_editor_document(
    doc_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
    provider: AssetProvider | None = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_owned_doc(session, user, doc_id)
    keys = secrets.get_user_keys(engine, _uid(user))
    if provider is None and not keys.replicate:
        raise HTTPException(409, "ajoute tes clés Replicate dans Réglages pour générer")
    service = EditorGenerationService(
        engine, provider=provider, downloader=downloader,
        replicate_token=keys.replicate,
    )
    background.add_task(service.generate_document, doc_id)
    return {"id": doc_id, "status": "scheduled"}


@app.post("/api/editor/documents/{doc_id}/bricks/{brick_id}/regenerate")
def regenerate_editor_brick(
    doc_id: int,
    brick_id: str,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
    provider: AssetProvider | None = Depends(get_asset_provider),
    downloader: Any = Depends(get_downloader),
) -> dict[str, Any]:
    _require_owned_doc(session, user, doc_id)
    keys = secrets.get_user_keys(engine, _uid(user))
    if provider is None and not keys.replicate:
        raise HTTPException(409, "ajoute tes clés Replicate dans Réglages pour générer")
    background.add_task(
        regenerate_brick, engine, doc_id, brick_id, provider, downloader,
        keys.replicate,
    )
    return {"id": doc_id, "brick_id": brick_id, "status": "scheduled"}


@app.get("/api/editor/documents/{doc_id}/render-model")
def editor_render_model(
    doc_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> dict[str, Any]:
    row = _require_owned_doc(session, user, doc_id)
    from ...editor import upgrade_document
    from ...editor.resolve import resolve

    doc = upgrade_document(json.loads(row.doc_json))
    asset_src = {
        a.beat: f"/api/assets/{a.id}/file"
        for a in AssetRepo(session).assets_by_document(doc_id)
        if a.status == "ready" and not a.excluded
    }
    model = resolve(doc, asset_src)
    data: dict[str, Any] = json.loads(model.model_dump_json())
    return data


@app.post("/api/editor/documents/{doc_id}/render")
def render_editor_document(
    doc_id: int,
    background: BackgroundTasks,
    session: Session = Depends(_session),
    user: User = Depends(require_user),
    engine: Engine = Depends(get_db_engine),
) -> dict[str, Any]:
    """Export MP4 via Remotion (subprocess Node) — planifié en tâche de fond."""
    _require_owned_doc(session, user, doc_id)
    from .services.remotion_render import render_document

    background.add_task(render_document, engine, doc_id)
    return {"id": doc_id, "status": "scheduled"}


@app.get("/api/editor/documents/{doc_id}/video")
def editor_document_video(
    doc_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> FileResponse:
    """Sert le MP4 final d'un document éditeur (rendu Remotion)."""
    row = _require_owned_doc(session, user, doc_id)
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
async def episode_events(
    episode_id: int,
    scope: str = "episode",
    engine: Engine = Depends(get_db_engine),
    user: User = Depends(require_user),
) -> StreamingResponse:
    # B.2 : vérifie l'ownership de la ressource suivie avant de s'abonner au bus
    # (le bus mélange épisodes et documents dans le même espace d'ids → 404 si
    # la ressource n'appartient pas à l'utilisateur). Session courte (le flux SSE
    # reste ouvert longtemps, on ne garde pas de session DB dessus).
    with Session(engine) as session:
        if scope == "doc":
            _require_owned_doc(session, user, episode_id)
        else:
            _require_owned_episode(session, user, episode_id)
    queue = bus.subscribe(episode_id)

    async def stream() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield bus.format_sse(event)
                except TimeoutError:
                    yield ": keep-alive\n\n"  # SSE comment heartbeat
        finally:
            bus.unsubscribe(episode_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/assets/{asset_id}/file")
def asset_file(
    asset_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Response:
    asset = _require_owned_asset(session, user, asset_id)
    if not asset.local_path or not storage.exists(asset.local_path):
        raise HTTPException(404, "asset file not available")
    return storage.serve(asset.local_path)


@app.get("/api/episodes/{episode_id}/video")
def episode_video(
    episode_id: int, session: Session = Depends(_session),
    user: User = Depends(require_user)
) -> Response:
    episode = _require_owned_episode(session, user, episode_id)
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
