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

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import create_engine  # noqa: E402

from src.studio.api import app as app_module  # noqa: E402
from src.studio.api.services.fakes import FakeAssetProvider  # noqa: E402
from src.studio.api.services.montage import MontageService  # noqa: E402
from src.studio.db.engine import init_db  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Run everything from a tmp cwd so exports/ and any db file stay isolated.
    monkeypatch.chdir(tmp_path)
    # Offline isolation : pas de vraie clé → décomposeur Fake déterministe.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)

    db_path = tmp_path / "studio_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    init_db(engine)

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

    # Serve an asset file.
    first_asset_id = assets[0]["id"]
    rf = client.get(f"/api/assets/{first_asset_id}/file")
    assert rf.status_code == 200
    assert rf.content == b"fake-bytes"


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
    final_path = r.json()["final_path"]
    assert final_path.endswith("final_video.mp4")

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
