"""Tests for the VCM Studio DB layer (models, repositories, migration).

Each test uses an isolated SQLite engine (temp file) so nothing touches the real
``studio.db`` and the legacy Aventure/golden tests stay independent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine

from src.studio.db.engine import get_session, init_db
from src.studio.db.migrate import migrate_exports, migrate_voices, run_migration
from src.studio.db.repositories import (
    AssetRepo,
    CostRepo,
    EpisodeRepo,
    JobRepo,
    ProjectRepo,
    ScriptRepo,
    VoiceRepo,
)
from sqlmodel import create_engine


@pytest.fixture()
def engine(tmp_path: Path) -> Engine:
    """Fresh file-backed SQLite engine with all tables created."""
    db_path = tmp_path / "test_studio.db"
    eng = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    init_db(eng)
    return eng


def test_init_db_is_idempotent(engine: Engine) -> None:
    init_db(engine)  # second call must not raise
    with get_session(engine) as session:
        assert ProjectRepo(session).list() == []


def test_project_repo_crud(engine: Engine) -> None:
    with get_session(engine) as session:
        repo = ProjectRepo(session)
        project = repo.create(name="horror-channel", settings_json='{"x":1}')
        assert project.id is not None
        assert repo.get(project.id).name == "horror-channel"
        assert repo.get_by_name("horror-channel").id == project.id
        assert len(repo.list()) == 1
        assert repo.delete(project.id) is True
        assert repo.get(project.id) is None


def test_episode_lifecycle(engine: Engine) -> None:
    with get_session(engine) as session:
        project = ProjectRepo(session).create(name="p1")
        repo = EpisodeRepo(session)
        ep = repo.create(project_id=project.id, title="ep1")
        assert ep.status == "draft"
        assert ep.draft_mode is True

        repo.update_status(ep.id, "assets")
        assert repo.get(ep.id).status == "assets"

        repo.set_final(ep.id, "/exports/p1/ep1/final_video.mp4", duration_s=42.0)
        refreshed = repo.get(ep.id)
        assert refreshed.status == "done"
        assert refreshed.final_path.endswith("final_video.mp4")
        assert refreshed.duration_s == 42.0

        assert len(repo.by_project(project.id)) == 1


def test_script_repo_latest(engine: Engine) -> None:
    with get_session(engine) as session:
        project = ProjectRepo(session).create(name="p")
        ep = EpisodeRepo(session).create(project_id=project.id, title="e")
        repo = ScriptRepo(session)
        repo.create(ep.id, json.dumps({"v": 1}))
        latest = repo.create(ep.id, json.dumps({"v": 2}), edited=True)
        found = repo.latest_for_episode(ep.id)
        assert found.id == latest.id
        assert found.edited is True
        assert json.loads(found.script_json)["v"] == 2


def test_asset_repo_queries(engine: Engine) -> None:
    with get_session(engine) as session:
        project = ProjectRepo(session).create(name="p")
        ep = EpisodeRepo(session).create(project_id=project.id, title="e")
        repo = AssetRepo(session)
        img = repo.create(ep.id, beat="base_image", kind="image", round_index=0)
        repo.create(ep.id, beat="hook", kind="video", round_index=0)

        assert len(repo.assets_by_episode(ep.id)) == 2
        images = repo.assets_by_episode(ep.id, kind="image")
        assert len(images) == 1 and images[0].id == img.id

        # Recording a downloaded local path flips status to ready.
        updated = repo.set_local_path(img.id, "/exports/p/e/base_image.png")
        assert updated.status == "ready"
        assert updated.local_path.endswith("base_image.png")
        assert "replicate.delivery" not in (updated.local_path or "")


def test_job_repo_status_transitions(engine: Engine) -> None:
    with get_session(engine) as session:
        project = ProjectRepo(session).create(name="p")
        ep = EpisodeRepo(session).create(project_id=project.id, title="e")
        asset = AssetRepo(session).create(ep.id, beat="hook", kind="video")
        repo = JobRepo(session)
        job = repo.create(
            asset_id=asset.id, model="prunaai/p-video", prediction_id="pred_123"
        )
        assert job.status == "pending"
        assert job.prediction_id == "pred_123"

        done = repo.mark_done(job.id, duration_s=12.5)
        assert done.status == "done" and done.duration_s == 12.5

        failed = repo.mark_failed(job.id, "boom")
        assert failed.status == "failed" and failed.error == "boom"


def test_voice_repo_crud(engine: Engine) -> None:
    with get_session(engine) as session:
        repo = VoiceRepo(session)
        v = repo.create(
            name="conteur",
            registre="conteur",
            description="gravelly storyteller",
            voice_id="R8_3HPKBKXB",
            sample_path="assets/voice-audition/conteur-sample-full.mp3",
        )
        assert v.id is not None
        assert repo.get_by_name("conteur").voice_id == "R8_3HPKBKXB"
        assert len(repo.list()) == 1
        assert repo.delete(v.id) is True


def test_cost_total_and_by_episode(engine: Engine) -> None:
    with get_session(engine) as session:
        project = ProjectRepo(session).create(name="p")
        ep1 = EpisodeRepo(session).create(project_id=project.id, title="e1")
        ep2 = EpisodeRepo(session).create(project_id=project.id, title="e2")

        asset1 = AssetRepo(session).create(ep1.id, beat="hook", kind="video")
        asset2 = AssetRepo(session).create(ep2.id, beat="hook", kind="video")
        job_repo = JobRepo(session)
        job1 = job_repo.create(asset_id=asset1.id, model="m1")
        job2 = job_repo.create(asset_id=asset2.id, model="m2")

        cost = CostRepo(session)
        cost.create(job1.id, model="m1", amount_usd=1.50, units=6, unit_kind="seconds")
        cost.create(job1.id, model="m1", amount_usd=0.50, units=1, unit_kind="images")
        cost.create(job2.id, model="m2", amount_usd=3.00, units=10, unit_kind="seconds")

        assert cost.total() == pytest.approx(5.00)
        assert cost.cost_total_by_episode(ep1.id) == pytest.approx(2.00)
        assert cost.cost_total_by_episode(ep2.id) == pytest.approx(3.00)


def test_migrate_voices_from_json(engine: Engine, tmp_path: Path) -> None:
    voice_json = tmp_path / "narrator_voice.json"
    voice_json.write_text(
        json.dumps(
            {
                "registre": "conteur",
                "description_prompt": "an old weathered storyteller voice",
                "source_sample": "assets/voice-audition/conteur-sample-full.mp3",
                "voice_id": "R8_3HPKBKXB",
                "local_preview": "assets/voice-audition/conteur-clone-preview.mp3",
            }
        ),
        encoding="utf-8",
    )

    created = migrate_voices(voice_json=voice_json, engine=engine)
    assert created == 1
    # Idempotent: second run creates nothing.
    assert migrate_voices(voice_json=voice_json, engine=engine) == 0

    with get_session(engine) as session:
        voice = VoiceRepo(session).get_by_name("conteur")
        assert voice is not None
        assert voice.voice_id == "R8_3HPKBKXB"
        assert voice.sample_path.endswith("conteur-sample-full.mp3")


def test_migrate_voices_missing_file(engine: Engine, tmp_path: Path) -> None:
    assert migrate_voices(voice_json=tmp_path / "nope.json", engine=engine) == 0


def test_migrate_exports_ignores_expiring_urls(
    engine: Engine, tmp_path: Path
) -> None:
    exports = tmp_path / "exports"
    inst = exports / "default_project" / "20260612_115619"
    inst.mkdir(parents=True)
    (inst / "base_image.png").write_bytes(b"png")
    (inst / "video.mp4").write_bytes(b"vid")
    (inst / "final_video.mp4").write_bytes(b"final")
    (inst / "character.mp3").write_bytes(b"aud")
    (inst / "metadata.json").write_text(
        json.dumps(
            {
                "freeze_image_prompt": "an image prompt",
                "video_prompt": "a video prompt",
                "video_url": "https://replicate.delivery/xezq/EXPIRES/output.mp4",
                "character_speech": "Choisi moi.",
            }
        ),
        encoding="utf-8",
    )

    counts = migrate_exports(exports_dir=exports, engine=engine)
    assert counts == {"projects": 1, "episodes": 1, "assets": 4}

    with get_session(engine) as session:
        project = ProjectRepo(session).get_by_name("default_project")
        assert project is not None
        episodes = EpisodeRepo(session).by_project(project.id)
        assert len(episodes) == 1
        ep = episodes[0]
        assert ep.status == "done"
        assert ep.final_path.endswith("final_video.mp4")

        assets = AssetRepo(session).assets_by_episode(ep.id)
        assert len(assets) == 4
        # RULE: never a replicate.delivery URL in the DB.
        for a in assets:
            assert "replicate.delivery" not in (a.local_path or "")
            assert a.local_path is not None and Path(a.local_path).exists()


def test_migrate_exports_idempotent(engine: Engine, tmp_path: Path) -> None:
    exports = tmp_path / "exports"
    inst = exports / "proj" / "inst1"
    inst.mkdir(parents=True)
    (inst / "base_image.png").write_bytes(b"png")

    first = migrate_exports(exports_dir=exports, engine=engine)
    second = migrate_exports(exports_dir=exports, engine=engine)
    assert first == {"projects": 1, "episodes": 1, "assets": 1}
    assert second == {"projects": 0, "episodes": 0, "assets": 0}


def test_run_migration_smoke(engine: Engine) -> None:
    # run_migration uses module-level default paths; just ensure it runs and
    # returns the expected keys against a clean engine without raising.
    result = run_migration(engine=engine)
    assert set(result) == {"voices", "projects", "episodes", "assets"}
