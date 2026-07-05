"""Integration tests for the VCM Studio FastAPI app (phase U1).

End-to-end through TestClient with NO network and NO FFmpeg:
  - the engine is overridden to a tmp SQLite file,
  - the asset provider is the offline FakeAssetProvider,
  - the downloader writes tiny placeholder files into a tmp exports dir,
  - the montage concatenator is stubbed.

Covers the full flow: project -> episode -> script (Fake) -> beats -> cost
-> generate assets (mocked) -> assets listing -> montage -> library.
"""

import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")

# Intégration FastAPI/DB lourde → skippée par défaut (cf. conftest, --runheavy).
pytestmark = pytest.mark.slow

from cryptography.fernet import Fernet  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import (  # noqa: E402
    Session,
    create_engine,
)

from src.studio.api import app as app_module  # noqa: E402
from src.studio.api.services import auth as auth_service  # noqa: E402
from src.studio.api.services.fakes import FakeAssetProvider  # noqa: E402
from src.studio.db.engine import init_db  # noqa: E402
from src.studio.db.repositories import UserRepo  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Run everything from a tmp cwd so exports/ and any db file stay isolated.
    monkeypatch.chdir(tmp_path)
    # Offline isolation : pas de vraie clé → décomposeur Fake déterministe.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    # B.2 : clé de chiffrement des clés API par-utilisateur (Fernet).
    monkeypatch.setenv("VCM_SECRET_KEY", Fernet.generate_key().decode())

    db_path = tmp_path / "studio_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    init_db(engine)

    # Auth (B.1) : toute l'API est derrière un login. On crée un admin dans la DB
    # de test et on ouvre la session sur le client (le cookie persiste ensuite).
    with Session(engine) as s:
        UserRepo(s).create(
            "admin@test.local",
            auth_service.hash_password("test-password"),
            is_admin=True,
        )

    fake_provider = FakeAssetProvider()

    def fake_downloader(url, folder, filename):
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, "wb") as f:
            f.write(b"fake-bytes")
        return path

    app_module.app.dependency_overrides[app_module.get_db_engine] = lambda: engine
    app_module.app.dependency_overrides[app_module.get_asset_provider] = (
        lambda: fake_provider
    )
    app_module.app.dependency_overrides[app_module.get_downloader] = (
        lambda: fake_downloader
    )

    with TestClient(app_module.app) as c:
        c.fake_provider = fake_provider  # type: ignore[attr-defined]
        c.engine = engine  # type: ignore[attr-defined]
        # Ouvre la session admin : le cookie signé persiste sur les requêtes suivantes.
        r = c.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "test-password"},
        )
        assert r.status_code == 200, r.text
        yield c

    app_module.app.dependency_overrides.clear()


def test_full_flow(client):
    # Project
    r = client.post("/api/projects", json={"name": "demo"})
    assert r.status_code == 200
    project_id = r.json()["id"]
    assert client.get("/api/projects").json()[0]["name"] == "demo"

    # Episode
    r = client.post(
        "/api/episodes",
        json={"project_id": project_id, "title": "ep1", "draft_mode": True},
    )
    assert r.status_code == 200
    episode_id = r.json()["id"]
    assert (
        client.get(f"/api/episodes?project_id={project_id}").json()[0]["title"]
        == "ep1"
    )
    # Single-episode fetch.
    one = client.get(f"/api/episodes/{episode_id}")
    assert one.status_code == 200
    assert one.json()["id"] == episode_id
    assert client.get("/api/episodes/99999").status_code == 404

    # Script (Fake decomposer, no OpenAI key)
    r = client.post(
        f"/api/episodes/{episode_id}/script",
        json={"prompt": "cave horror", "char_left_name": "Étienne", "char_right_name": "Marc"},
    )
    assert r.status_code == 200
    script = r.json()
    assert script["char_left_name"] == "Étienne"
    assert len(script["rounds"]) == 3

    # Beats
    beats = client.get(f"/api/episodes/{episode_id}/beats").json()
    assert len(beats["assets"]) == 56

    # Cost estimate (draft) before generation: actual is 0.
    cost = client.get(f"/api/episodes/{episode_id}/cost").json()
    assert cost["estimated_usd"] > 0
    assert cost["actual_usd"] == 0.0
    assert {b["unit_kind"] for b in cost["breakdown"]} == {"image", "second", "kchar"}

    # Generate assets (background task runs synchronously after the response).
    r = client.post(f"/api/episodes/{episode_id}/assets/generate")
    assert r.status_code == 200

    # Provider was called offline; assets are persisted with local paths.
    assert len(client.fake_provider.image_calls) == 23
    assert len(client.fake_provider.video_calls) == 16
    assert len(client.fake_provider.voice_calls) == 17

    assets = client.get(f"/api/episodes/{episode_id}/assets").json()
    assert len(assets) == 56
    assert all(a["status"] == "ready" for a in assets)
    assert all(a["local_path"] for a in assets)

    # Image-first: each video reused the frame generated just before it.
    for call in client.fake_provider.video_calls:
        assert call["image"].startswith("https://fake.local/")

    # Actual cost is recorded and matches the pre-flight estimate (a tiny
    # divergence is expected: the estimate rounds the total char count once,
    # while actuals round per narration beat).
    cost2 = client.get(f"/api/episodes/{episode_id}/cost").json()
    assert cost2["actual_usd"] == pytest.approx(cost2["estimated_usd"], rel=1e-3)
    # Per-node ACTUAL cost (after generation): one row per generated asset, each
    # tagged with its source, and the total is the sum of the real node costs
    # (not a re-derived estimate).
    nodes = cost2["nodes"]
    assert len(nodes) == 56
    assert all(n["source"] in ("provider", "compute", "estimate") for n in nodes)
    assert all(isinstance(n["is_estimate"], bool) for n in nodes)
    assert cost2["actual_usd"] == pytest.approx(
        sum(n["amount_usd"] for n in nodes), rel=1e-9
    )

    # Serve an asset file.
    first_asset_id = assets[0]["id"]
    rf = client.get(f"/api/assets/{first_asset_id}/file")
    assert rf.status_code == 200
    assert rf.content == b"fake-bytes"


def test_editor_document_from_script(client):
    """R1 câblé : le script d'un épisode → document de briques ClipBrick persistant."""
    pid = client.post("/api/projects", json={"name": "p"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "cave"})

    r = client.post(f"/api/episodes/{eid}/editor-document")
    assert r.status_code == 200
    body = r.json()
    assert body["episode_id"] == eid and body["project_id"] == pid

    bricks = body["doc"]["bricks"]
    assert all(b["type"] == "clip" for b in bricks)  # arbre ClipBrick, pas de plat
    assert {b["kind"] for b in bricks} == {"video", "photo"}
    ids = [b["id"] for b in bricks]
    assert ids[0] == "ep_intro" and ids[-1] == "ep_epilogue"

    # persisté + relisible via la route éditeur générique
    doc_id = body["id"]
    got = client.get(f"/api/editor/documents/{doc_id}").json()
    assert [b["id"] for b in got["doc"]["bricks"]] == ids


def test_editor_document_requires_script(client):
    pid = client.post("/api/projects", json={"name": "p2"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e2"}
    ).json()["id"]
    r = client.post(f"/api/episodes/{eid}/editor-document")
    assert r.status_code == 404  # pas de script encore


def test_generate_editor_document_clips_idempotent(client):
    """R1b : le document de briques se génère (image→motion→narration), idempotent."""
    from sqlmodel import Session as _S

    from src.studio.db.repositories import AssetRepo

    pid = client.post("/api/projects", json={"name": "g"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "cave"})
    doc_id = client.post(f"/api/episodes/{eid}/editor-document").json()["id"]

    # 1re génération : un appel run_model par nœud (couverture 1:1 du plan = 56).
    assert client.post(f"/api/editor/documents/{doc_id}/generate").status_code == 200
    n_calls = len(client.fake_provider.run_calls)
    assert n_calls == 56

    with _S(client.engine) as s:
        assets = AssetRepo(s).assets_by_document(doc_id)
    assert len(assets) == 56
    assert all(a.status == "ready" and a.local_path for a in assets)
    assert {a.kind for a in assets} == {"image", "video", "audio"}
    beats = [a.beat for a in assets]
    assert any(b.endswith(".image") for b in beats)
    assert any(b.endswith(".motion") for b in beats)
    assert any(b.endswith("__narr") for b in beats)

    # image-first : chaque motion a reçu l'URL d'une image en entrée.
    motion_calls = [p for _m, p in client.fake_provider.run_calls if "duration" in p]
    assert motion_calls
    assert all(c["image"].startswith("https://fake.local/") for c in motion_calls)

    # IDEMPOTENCE : re-générer ne relance AUCUN appel (tout est prêt + sur disque).
    client.post(f"/api/editor/documents/{doc_id}/generate")
    assert len(client.fake_provider.run_calls) == n_calls

    # Régénération ciblée d'une brique VIDÉO + narration → exactement 3 nœuds.
    client.post(f"/api/editor/documents/{doc_id}/bricks/r0_action/regenerate")
    assert len(client.fake_provider.run_calls) == n_calls + 3


def test_regenerate_single_asset(client):
    pid = client.post("/api/projects", json={"name": "p"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "x"})
    client.post(f"/api/episodes/{eid}/assets/generate")

    assets = client.get(f"/api/episodes/{eid}/assets").json()
    before = len(client.fake_provider.image_calls)
    img_asset = next(a for a in assets if a["kind"] == "image")

    r = client.post(f"/api/assets/{img_asset['id']}/regenerate")
    assert r.status_code == 200
    # One more provider image call happened.
    assert len(client.fake_provider.image_calls) == before + 1


def test_montage_and_library(client):
    pid = client.post("/api/projects", json={"name": "p"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "x"})
    client.post(f"/api/episodes/{eid}/assets/generate")

    # Stub the montage concatenator (no MoviePy / FFmpeg).
    def fake_concat(paths, output_path):
        with open(output_path, "wb") as f:
            f.write(b"final")
        return 42.0

    # Library empty before montage.
    assert client.get("/api/library").json() == []

    # Override the montage backend by monkeypatching the service default.
    import src.studio.api.services.montage as montage_mod
    orig = montage_mod._moviepy_concat
    montage_mod._moviepy_concat = fake_concat
    try:
        r = client.post(f"/api/episodes/{eid}/montage")
    finally:
        montage_mod._moviepy_concat = orig
    assert r.status_code == 200
    assert r.json()["status"] == "scheduled"
    # Montage runs as a BackgroundTask; the TestClient completes it before the
    # POST returns (still under the fake_concat patch), so the final video and
    # library entry below are already produced.

    lib = client.get("/api/library").json()
    assert len(lib) == 1
    assert lib[0]["episode_id"] == eid
    assert lib[0]["duration_s"] == 42.0

    # Serve the final video.
    rv = client.get(f"/api/episodes/{eid}/video")
    assert rv.status_code == 200
    assert rv.content == b"final"


def test_errors(client):
    # Episode under missing project.
    assert client.post(
        "/api/episodes", json={"project_id": 999, "title": "x"}
    ).status_code == 404
    # Beats/cost before a script exists.
    pid = client.post("/api/projects", json={"name": "p"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    assert client.get(f"/api/episodes/{eid}/beats").status_code == 404
    # Montage with no assets -> conflict.
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "x"})
    assert client.post(f"/api/episodes/{eid}/montage").status_code == 409


def test_settings_keys_per_user_encrypted(client):
    # B.2 : clés par-utilisateur, chiffrées au repos, jamais renvoyées en clair.
    assert client.get("/api/settings/keys").json() == {
        "openai_set": False,
        "replicate_set": False,
    }
    r = client.put("/api/settings/keys", json={"openai": "sk-test-123"})
    assert r.status_code == 200
    assert r.json() == {"openai_set": True, "replicate_set": False}
    # Statut persisté + masqué : la valeur n'apparaît jamais dans la réponse.
    assert client.get("/api/settings/keys").json()["openai_set"] is True
    assert "sk-test-123" not in client.get("/api/settings/keys").text
    # Un champ vide ne vide PAS une clé existante.
    client.put("/api/settings/keys", json={"openai": ""})
    assert client.get("/api/settings/keys").json()["openai_set"] is True
    # Chiffrement au repos : le ciphertext en DB ≠ le secret, mais déchiffrable.
    with Session(client.engine) as s:
        from src.studio.db.repositories import UserApiKeyRepo, UserRepo

        admin = UserRepo(s).get_by_email("admin@test.local")
        row = UserApiKeyRepo(s).get(admin.id, "openai")
    assert row is not None
    assert row.ciphertext != "sk-test-123"
    fernet = Fernet(os.environ["VCM_SECRET_KEY"].encode())
    assert fernet.decrypt(row.ciphertext.encode()).decode() == "sk-test-123"


def _register(client, email, password="password123"):
    """Repart d'une session vierge et ouvre une session pour ``email``."""
    client.post("/api/auth/logout")
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_upload_photo(client):
    # Upload d'une photo (Phase 3) → renvoie une ref stockée, auth requise.
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 256
    r = client.post(
        "/api/uploads", files={"file": ("photo.png", png, "image/png")}
    )
    assert r.status_code == 200, r.text
    ref = r.json()["ref"]
    assert ref
    from src.features import storage

    assert storage.exists(ref)
    # Fichier vide → 422.
    assert client.post(
        "/api/uploads", files={"file": ("empty.png", b"", "image/png")}
    ).status_code == 422
    # Sans session → 401.
    client.post("/api/auth/logout")
    assert client.post(
        "/api/uploads", files={"file": ("x.png", png, "image/png")}
    ).status_code == 401


def test_resolve_media_value_unit():
    # Résolution des valeurs média (Phase 3), sans réseau.
    from src.studio.api.services.editor_generation import _resolve_media_value

    assert _resolve_media_value("https://x/y.png", None) == "https://x/y.png"
    assert _resolve_media_value("", None) is None
    # Une valeur non-fichier (ex. un prompt) n'est pas résolue.
    assert _resolve_media_value("juste un prompt", None) is None


def test_data_isolation_between_users(client):
    # Alice crée un projet + épisode ; Bob ne doit RIEN en voir (404, pas 403).
    _register(client, "alice@test.local")
    pid = client.post("/api/projects", json={"name": "alice-proj"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "x"})

    _register(client, "bob@test.local")
    # Bob ne voit pas le projet/épisode d'Alice dans ses listes.
    assert client.get("/api/projects").json() == []
    assert client.get("/api/episodes").json() == []
    assert client.get("/api/library").json() == []
    # Accès direct par id → 404 (ne pas divulguer l'existence).
    assert client.get(f"/api/episodes/{eid}").status_code == 404
    assert client.get(f"/api/episodes/{eid}/script").status_code == 404
    assert client.get(f"/api/episodes/{eid}/assets").status_code == 404
    assert client.get(f"/api/episodes/{eid}/video").status_code == 404
    assert client.post(f"/api/episodes/{eid}/montage").status_code == 404
    assert client.post(
        f"/api/episodes/{eid}/assets/generate"
    ).status_code == 404
    assert client.post(
        "/api/episodes", json={"project_id": pid, "title": "x"}
    ).status_code == 404
    # Ses propres clés sont indépendantes de celles d'Alice.
    assert client.get("/api/settings/keys").json() == {
        "openai_set": False,
        "replicate_set": False,
    }


def test_admin_sees_all(client):
    # Le fixture est admin. Alice crée un projet ; l'admin le voit (bypass).
    _register(client, "alice@test.local")
    pid = client.post("/api/projects", json={"name": "alice-proj"}).json()["id"]
    client.post("/api/auth/logout")
    client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "test-password"},
    )
    assert any(p["id"] == pid for p in client.get("/api/projects").json())
    assert client.get(f"/api/episodes?project_id={pid}").status_code == 200


def test_generate_without_key_returns_409(client):
    # Sans provider injecté ni clé Replicate → 409 « ajoute tes clés ».
    _register(client, "carol@test.local")
    pid = client.post("/api/projects", json={"name": "c"}).json()["id"]
    eid = client.post(
        "/api/episodes", json={"project_id": pid, "title": "e"}
    ).json()["id"]
    client.post(f"/api/episodes/{eid}/script", json={"prompt": "x"})
    # Retire l'override du provider fake → chemin prod (provider None).
    app_module.app.dependency_overrides.pop(app_module.get_asset_provider, None)
    try:
        r = client.post(f"/api/episodes/{eid}/assets/generate")
        assert r.status_code == 409
    finally:
        app_module.app.dependency_overrides[app_module.get_asset_provider] = (
            lambda: client.fake_provider
        )


# --- Auth (Phase B.1) -------------------------------------------------------


def test_auth_required_without_session(client):
    # Une fois déconnecté, toute l'API /api (hors auth) est fermée.
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_register_login_me_logout_flow(client):
    # Le fixture est connecté en admin ; on repart d'une session vierge.
    client.post("/api/auth/logout")
    # Inscription (compte non-admin) → ouvre la session.
    r = client.post(
        "/api/auth/register",
        json={"email": "Bob@Test.local", "password": "password123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["email"] == "bob@test.local"  # normalisé en minuscules
    assert body["is_admin"] is False
    assert "password" not in r.text and "hash" not in r.text
    # /me reflète l'utilisateur courant.
    assert client.get("/api/auth/me").json()["email"] == "bob@test.local"
    # Déconnexion → 401 ensuite.
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    # Reconnexion.
    assert client.post(
        "/api/auth/login",
        json={"email": "bob@test.local", "password": "password123"},
    ).status_code == 200


def test_register_validation_and_duplicates(client):
    client.post("/api/auth/logout")
    # Mot de passe trop court.
    assert client.post(
        "/api/auth/register",
        json={"email": "x@test.local", "password": "short"},
    ).status_code == 422
    # Email invalide.
    assert client.post(
        "/api/auth/register",
        json={"email": "nope", "password": "password123"},
    ).status_code == 422
    # Doublon (l'admin du fixture existe déjà).
    assert client.post(
        "/api/auth/register",
        json={"email": "admin@test.local", "password": "password123"},
    ).status_code == 409
    # Mauvais mot de passe.
    assert client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "wrong"},
    ).status_code == 401
