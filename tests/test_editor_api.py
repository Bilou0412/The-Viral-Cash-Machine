"""Integration tests for the editor backend routes (E5).

End-to-end through TestClient, fully offline:
  - engine overridden to a tmp SQLite file,
  - asset provider = FakeAssetProvider (records run_calls, fake URLs),
  - downloader writes tiny placeholder files into a tmp exports dir.

Covers: create project + editor document, PUT a doc with one image brick,
POST generate (background task runs synchronously after the response), assert an
Asset row with editor_document_id + beat == brick.id is created and run_calls
recorded, then GET render-model returns a clip referencing the asset file URL.

Needs sqlalchemy/fastapi → runs in Docker/CI.
"""

import os

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlmodel")

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, create_engine  # noqa: E402

from src.studio.api import app as app_module  # noqa: E402
from src.studio.api.services.fakes import FakeAssetProvider  # noqa: E402
from src.studio.db.engine import init_db  # noqa: E402
from src.studio.db.repositories import AssetRepo  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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


def _image_doc():
    return {
        "schema_version": 1,
        "title": "ed1",
        "canvas": {"width": 1080, "height": 1920, "fps": 30},
        "global_context": {
            "text": "une histoire",
            "characters": {},
            "art_direction": "",
            "extra": {},
        },
        "tracks": [],
        "bricks": [
            {
                "id": "hero",
                "type": "image",
                "model_ref": "bytedance/seedream-4.5",
                "params": {"prompt": "a castle", "aspect_ratio": "9:16"},
                "context_overrides": None,
                "preset_id": None,
                "layers": [],
                "placement": {"track": 0, "start": 0.0, "duration": 3.0},
            }
        ],
    }


def test_editor_document_crud_generate_and_render_model(client):
    project_id = client.post("/api/projects", json={"name": "demo"}).json()["id"]

    # Create an empty document.
    r = client.post(
        "/api/editor/documents",
        json={"project_id": project_id, "title": "ed1"},
    )
    assert r.status_code == 200
    doc_id = r.json()["id"]
    assert r.json()["doc"]["bricks"] == []

    # Listing.
    docs = client.get(
        f"/api/editor/documents?project_id={project_id}"
    ).json()
    assert any(d["id"] == doc_id for d in docs)

    # PUT a document with one image brick.
    r = client.put(
        f"/api/editor/documents/{doc_id}",
        json={"title": "ed1", "doc": _image_doc()},
    )
    assert r.status_code == 200
    assert r.json()["doc"]["bricks"][0]["id"] == "hero"

    # GET round-trips through upgrade_document.
    got = client.get(f"/api/editor/documents/{doc_id}").json()
    assert got["doc"]["bricks"][0]["model_ref"] == "bytedance/seedream-4.5"

    # Generate (background task runs synchronously after the response).
    r = client.post(f"/api/editor/documents/{doc_id}/generate")
    assert r.status_code == 200

    # Provider was called offline with the brick's model + compiled prompt.
    assert len(client.fake_provider.run_calls) == 1
    model_ref, params = client.fake_provider.run_calls[0]
    assert model_ref == "bytedance/seedream-4.5"
    assert "a castle" in params["prompt"]
    assert "une histoire" in params["prompt"]  # global context folded in

    # An Asset row tied to the document + beat == brick id was created.
    with Session(client.engine) as session:
        assets = AssetRepo(session).assets_by_document(doc_id)
    assert len(assets) == 1
    asset = assets[0]
    assert asset.editor_document_id == doc_id
    assert asset.beat == "hero"
    assert asset.kind == "image"
    assert asset.status == "ready"
    assert asset.local_path

    # render-model references the asset file URL for the brick.
    rm = client.get(f"/api/editor/documents/{doc_id}/render-model").json()
    assert len(rm["clips"]) == 1
    clip = rm["clips"][0]
    assert clip["id"] == "hero"
    assert clip["media"] == "image"
    assert clip["src"] == f"/api/assets/{asset.id}/file"
    assert rm["total_duration"] == 3.0

    # Serve the underlying file.
    rf = client.get(f"/api/assets/{asset.id}/file")
    assert rf.status_code == 200
    assert rf.content == b"fake-bytes"


def test_editor_missing_required_param_marks_failed(client):
    project_id = client.post("/api/projects", json={"name": "p"}).json()["id"]
    doc_id = client.post(
        "/api/editor/documents", json={"project_id": project_id, "title": "e"}
    ).json()["id"]

    # A voice brick missing the required voice_id -> asset failed, render-model
    # has no ready clip src.
    doc = {
        "bricks": [
            {
                "id": "vo",
                "type": "voice",
                "model_ref": "minimax/speech-2.8-turbo",
                "params": {"text": "bonjour"},
                "placement": {"track": 0, "start": 0.0, "duration": 2.0},
            }
        ]
    }
    client.put(f"/api/editor/documents/{doc_id}", json={"doc": doc})
    client.post(f"/api/editor/documents/{doc_id}/generate")

    # Provider was never called (validation failed first).
    assert client.fake_provider.run_calls == []
    with Session(client.engine) as session:
        assets = AssetRepo(session).assets_by_document(doc_id)
    assert len(assets) == 1
    assert assets[0].status != "ready"

    rm = client.get(f"/api/editor/documents/{doc_id}/render-model").json()
    # The clip exists (from the doc) but has no resolved src (asset not ready).
    assert rm["clips"][0]["src"] is None


def test_editor_404s(client):
    assert client.get("/api/editor/documents/999").status_code == 404
    assert (
        client.put(
            "/api/editor/documents/999", json={"doc": {"bricks": []}}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/editor/documents", json={"project_id": 999, "title": "x"}
        ).status_code
        == 404
    )
