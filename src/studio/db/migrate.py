"""Best-effort migration of legacy file-based state into the studio DB.

Two sources are imported, idempotently:

1. ``assets/narrator_voice.json`` -> a :class:`VoiceProfile` row.
2. ``exports/{project}/{instance}/`` directories -> :class:`Project`,
   :class:`Episode` and :class:`Asset` rows.

RULE: only on-disk paths are stored. The expiring ``*_url`` fields found in
legacy ``metadata.json`` (``replicate.delivery`` links) are deliberately ignored.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.engine import Engine

from src.studio.db.engine import get_session, init_db
from src.studio.db.repositories import (
    AssetRepo,
    EpisodeRepo,
    ProjectRepo,
    VoiceRepo,
)

# Repository root (…/src/studio/db/migrate.py -> repo root is parents[3]).
REPO_ROOT = Path(__file__).resolve().parents[3]
NARRATOR_VOICE_JSON = REPO_ROOT / "assets" / "narrator_voice.json"
EXPORTS_DIR = REPO_ROOT / "exports"

# Asset file name -> (kind, beat).
ASSET_FILES: dict[str, tuple[str, str]] = {
    "base_image.png": ("image", "base_image"),
    "video.mp4": ("video", "hook"),
    "final_video.mp4": ("video", "final"),
    "character.mp3": ("audio", "character"),
    "narrator.mp3": ("audio", "narrator"),
}


def migrate_voices(
    voice_json: Path = NARRATOR_VOICE_JSON, engine: Engine | None = None
) -> int:
    """Import ``narrator_voice.json`` into :class:`VoiceProfile`.

    Returns the number of rows created. Idempotent: skips if a voice with the
    same ``voice_id`` (or name) already exists. Returns 0 if the file is absent.
    """
    if not voice_json.exists():
        return 0

    data = json.loads(voice_json.read_text(encoding="utf-8"))
    voice_id = data.get("voice_id")
    name = data.get("registre") or voice_json.stem
    sample = data.get("source_sample") or data.get("local_preview")

    created = 0
    with get_session(engine) as session:
        repo = VoiceRepo(session)
        existing = repo.get_by_name(name)
        if existing is None and voice_id is not None:
            # Also dedupe on voice_id across any name.
            for v in repo.list():
                if v.voice_id == voice_id:
                    existing = v
                    break
        if existing is None:
            repo.create(
                name=name,
                registre=data.get("registre"),
                description=data.get("description_prompt"),
                voice_id=voice_id,
                sample_path=sample,
            )
            created = 1
    return created


def migrate_exports(
    exports_dir: Path = EXPORTS_DIR, engine: Engine | None = None
) -> dict[str, int]:
    """Scan ``exports/`` and create Project/Episode/Asset rows (best-effort).

    Only files that actually exist on disk are recorded as assets; expiring
    ``replicate.delivery`` URLs in ``metadata.json`` are ignored. Idempotent:
    re-running does not duplicate projects, episodes or assets.

    Returns counts: ``{"projects", "episodes", "assets"}``.
    """
    counts = {"projects": 0, "episodes": 0, "assets": 0}
    if not exports_dir.exists():
        return counts

    with get_session(engine) as session:
        project_repo = ProjectRepo(session)
        episode_repo = EpisodeRepo(session)
        asset_repo = AssetRepo(session)

        for project_dir in sorted(p for p in exports_dir.iterdir() if p.is_dir()):
            project = project_repo.get_by_name(project_dir.name)
            if project is None:
                project = project_repo.create(name=project_dir.name)
                counts["projects"] += 1
            assert project.id is not None

            existing_titles = {
                ep.title for ep in episode_repo.by_project(project.id)
            }

            for inst_dir in sorted(
                d for d in project_dir.iterdir() if d.is_dir()
            ):
                if inst_dir.name in existing_titles:
                    continue

                final = inst_dir / "final_video.mp4"
                status = "done" if final.exists() else "assets"
                episode = episode_repo.create(
                    project_id=project.id,
                    title=inst_dir.name,
                    status=status,
                    draft_mode=False,
                )
                counts["episodes"] += 1
                assert episode.id is not None

                if final.exists():
                    episode_repo.set_final(episode.id, str(final))

                metadata = _load_metadata(inst_dir)
                for filename, (kind, beat) in ASSET_FILES.items():
                    path = inst_dir / filename
                    if not path.exists():
                        continue
                    prompt = _prompt_for_beat(metadata, beat)
                    asset_repo.create(
                        episode_id=episode.id,
                        beat=beat,
                        kind=kind,
                        prompt=prompt,
                        local_path=str(path),
                        status="ready",
                        draft=False,
                    )
                    counts["assets"] += 1

    return counts


def _load_metadata(inst_dir: Path) -> dict[str, object]:
    """Read ``metadata.json`` if present, else return an empty dict."""
    meta_path = inst_dir / "metadata.json"
    if not meta_path.exists():
        return {}
    try:
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _prompt_for_beat(
    metadata: dict[str, object], beat: str
) -> str | None:
    """Pull the relevant prompt/text out of legacy metadata for a beat."""
    key = {
        "base_image": "freeze_image_prompt",
        "hook": "video_prompt",
        "final": "video_prompt",
        "character": "character_speech",
        "narrator": "narration_script",
    }.get(beat)
    if key is None:
        return None
    value = metadata.get(key)
    return value if isinstance(value, str) else None


def run_migration(engine: Engine | None = None) -> dict[str, int]:
    """Run the full migration (init DB, voices, exports). Returns row counts."""
    init_db(engine)
    result = {"voices": migrate_voices(engine=engine)}
    result.update(migrate_exports(engine=engine))
    return result


if __name__ == "__main__":
    summary = run_migration()
    print("Migration complete:", summary)
