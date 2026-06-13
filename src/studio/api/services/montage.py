"""Montage service — assemble an episode's video beats into one file.

For phase U1 this is a straightforward concatenation of the episode's ready video
assets in timeline order (rounds ascending, beat order within a round, epilogue
last). The richer cinematic assembly (intro, subtitles, nameplates, countdown)
already lives in scripts/compiler.py and can be wired in later; the contract here
is: produce a single `final_video.mp4` and record it on the Episode.

The concatenation backend is injectable so tests run without MoviePy/FFmpeg.
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional, Sequence

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ...db.models import Asset
from ...db.repositories import AssetRepo, EpisodeRepo, ProjectRepo

# (ordered local video paths, output path) -> duration seconds.
Concatenator = Callable[[Sequence[str], str], float]

# Beat ordering within a round (matches the generation timeline).
_BEAT_ORDER = {
    "action.motion": 0,
    "environment.motion": 1,
    "character.motion": 2,
    "fatal.motion": 3,
    "survival.motion": 4,
}


def _moviepy_concat(paths: Sequence[str], output_path: str) -> float:
    """Concatenate clips with MoviePy. Imported lazily (heavy, needs FFmpeg)."""
    from moviepy import VideoFileClip, concatenate_videoclips

    clips = [VideoFileClip(p) for p in paths]
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    duration = float(final.duration)
    final.close()
    for clip in clips:
        clip.close()
    return duration


def _ordered_video_assets(assets: Sequence[Asset]) -> List[Asset]:
    """Episode video assets in timeline order: rounds then epilogue, beat order."""
    videos = [a for a in assets if a.kind == "video" and a.local_path]

    def key(a: Asset) -> tuple[int, int]:
        # round_index None (epilogue) sorts last.
        r = a.round_index if a.round_index is not None else 999
        return (r, _BEAT_ORDER.get(a.beat, 99))

    return sorted(videos, key=key)


class MontageService:
    """Assembles ready video beats of an episode into one final video."""

    def __init__(
        self, engine: Engine, concatenator: Optional[Concatenator] = None
    ) -> None:
        self.engine = engine
        self.concatenator = concatenator or _moviepy_concat

    def assemble(self, episode_id: int) -> str:
        """Concatenate the episode's video beats; record + return the final path."""
        with Session(self.engine) as session:
            episode = EpisodeRepo(session).get(episode_id)
            if episode is None:
                raise ValueError(f"episode {episode_id} not found")
            project = ProjectRepo(session).get(episode.project_id)
            project_name = project.name if project else f"project_{episode.project_id}"
            assets = AssetRepo(session).assets_by_episode(episode_id)

        ordered = _ordered_video_assets(assets)
        if not ordered:
            raise ValueError(
                f"episode {episode_id} has no ready video assets to assemble"
            )

        out_dir = os.path.join("exports", project_name, f"episode_{episode_id}")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "final_video.mp4")

        paths = [a.local_path for a in ordered if a.local_path]
        duration = self.concatenator(paths, output_path)

        with Session(self.engine) as session:
            EpisodeRepo(session).set_final(episode_id, output_path, duration)
        return output_path
