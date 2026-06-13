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
from .paths import episode_dir

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

        out_dir = episode_dir(project_name, episode_id)
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "final_video.mp4")

        paths = [a.local_path for a in ordered if a.local_path]
        duration = self.concatenator(paths, output_path)

        with Session(self.engine) as session:
            EpisodeRepo(session).set_final(episode_id, output_path, duration)
        return output_path

    # -- Rich cinematic montage (timers, nameplates, subtitles) ---------------

    def assemble_rich(self, episode_id: int) -> str:
        """Montage qualité via le compositeur Aventure MoviePy.

        Monte chaque round (action/environnement/face-cam/écran de choix +
        timer 3-2-1/issues) avec plaques de nom + sous-titres Whisper + narration
        conteur, puis l'épilogue, et concatène en `final_video.mp4`.

        Repli automatique sur `assemble` (concat simple) si les prérequis
        manquent (pas de script, assets/fichiers incomplets) — ça garde la
        compatibilité avec les tests offline.
        """
        import json

        from ...db.repositories import ScriptRepo
        from ....features.scripting.adventure import AdventureScript
        from ....features.transcription.whisper import WhisperTranscriber
        from ....features.compositing.adventure_compositor import (
            RoundAssets,
            compose_narrated_segment,
            compose_round,
        )

        with Session(self.engine) as session:
            episode = EpisodeRepo(session).get(episode_id)
            if episode is None:
                raise ValueError(f"episode {episode_id} not found")
            project = ProjectRepo(session).get(episode.project_id)
            project_name = project.name if project else f"project_{episode.project_id}"
            assets = AssetRepo(session).assets_by_episode(episode_id)
            row = ScriptRepo(session).latest_for_episode(episode_id)

        if row is None:
            return self.assemble(episode_id)
        try:
            script = AdventureScript.model_validate_json(row.script_json)
        except Exception:
            return self.assemble(episode_id)

        # (round_index, beat) -> local_path, only files that actually exist.
        by_key = {
            (a.round_index, a.beat): a.local_path
            for a in assets
            if a.local_path and os.path.exists(a.local_path)
        }

        def g(ri: Optional[int], beat: str) -> Optional[str]:
            return by_key.get((ri, beat))

        follower = script.char_left_name
        out_dir = episode_dir(project_name, episode_id)
        os.makedirs(out_dir, exist_ok=True)
        work = os.path.join(out_dir, "_montage")
        os.makedirs(work, exist_ok=True)
        transcriber = WhisperTranscriber()

        # Prerequisite check: every round needs its video/image beats on disk.
        n_rounds = len(script.rounds)
        req_video_beats = (
            "action.motion", "environment.motion", "character.motion",
            "choice.0", "choice.1", "fatal.motion", "survival.motion",
        )
        for ri in range(n_rounds):
            if any(g(ri, b) is None for b in req_video_beats):
                return self.assemble(episode_id)

        # Rich compositing (MoviePy). On any failure (e.g. unreadable media in
        # offline tests), degrade gracefully to the simple concat.
        try:
            round_files: List[str] = []
            for ri in range(n_rounds):
                rf = os.path.join(work, f"round_{ri}.mp4")
                compose_round(
                    RoundAssets(
                        action_video=g(ri, "action.motion") or "",
                        environment_video=g(ri, "environment.motion") or "",
                        facecam_video=g(ri, "character.motion") or "",
                        choice_a_image=g(ri, "choice.0") or "",
                        choice_b_image=g(ri, "choice.1") or "",
                        fatal_video=g(ri, "fatal.motion") or "",
                        survival_video=g(ri, "survival.motion") or "",
                        narr_action=g(ri, "action.narration") or "",
                        narr_environment=g(ri, "environment.narration") or "",
                        narr_choice=g(ri, "choice.narration") or "",
                        narr_fatal=g(ri, "fatal.narration") or "",
                        narr_survival=g(ri, "survival.narration") or "",
                    ),
                    follower, transcriber, rf, workdir=work,
                )
                round_files.append(rf)

            epi_video = g(None, "epilogue.motion")
            if epi_video:
                ef = os.path.join(work, "epilogue.mp4")
                compose_narrated_segment(
                    epi_video, g(None, "epilogue.narration") or "",
                    script.char_right_name, transcriber, ef, workdir=work,
                )
                round_files.append(ef)

            output_path = os.path.join(out_dir, "final_video.mp4")
            duration = self.concatenator(round_files, output_path)
        except Exception:
            return self.assemble(episode_id)

        with Session(self.engine) as session:
            EpisodeRepo(session).set_final(episode_id, output_path, duration)
        return output_path
