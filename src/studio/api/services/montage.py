"""Montage service — assemble an episode's video beats into one file.

For phase U1 this is a straightforward concatenation of the episode's ready video
assets in timeline order (rounds ascending, beat order within a round, epilogue
last). The richer cinematic assembly (intro, subtitles, nameplates, countdown)
already lives in scripts/compiler.py and can be wired in later; the contract here
is: produce a single `final_video.mp4` and record it on the Episode.

The concatenation backend is injectable so tests run without MoviePy/FFmpeg.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....features import storage
from ...db.models import Asset
from ...db.repositories import AssetRepo, EpisodeRepo, ProjectRepo
from .paths import episode_dir

logger = logging.getLogger(__name__)

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


def _ordered_video_assets(assets: Sequence[Asset]) -> list[Asset]:
    """Episode video assets in timeline order: intro, rounds, then epilogue.

    M2 : l'intro (beat="intro", round_index=None) DOIT passer en premier — sans ce
    cas spécial elle retombait en dernier (round_index None → 999), ce qui plaçait
    l'intro à la fin de la vidéo lors d'un repli sur la concat simple.
    """
    videos = [
        a for a in assets
        if a.kind == "video" and a.local_path and not a.excluded
    ]

    def key(a: Asset) -> tuple[int, int]:
        if a.beat == "intro":      # toujours en tête
            return (-1, 0)
        # round_index None (epilogue) sorts last.
        r = a.round_index if a.round_index is not None else 999
        return (r, _BEAT_ORDER.get(a.beat, 99))

    return sorted(videos, key=key)


class MontageService:
    """Assembles ready video beats of an episode into one final video."""

    def __init__(
        self, engine: Engine, concatenator: Concatenator | None = None
    ) -> None:
        self.engine = engine
        self.concatenator = concatenator or _moviepy_concat

    def has_renderable_inputs(self, episode_id: int) -> bool:
        """True if the episode has ≥1 ready video asset to montage.

        Mirrors ``assemble``'s precondition so the API can validate synchronously
        (and return 409) BEFORE scheduling the montage off the request cycle.
        """
        with Session(self.engine) as session:
            assets = AssetRepo(session).assets_by_episode(episode_id)
        return bool(_ordered_video_assets(assets))

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

        paths = [storage.materialize(a.local_path) for a in ordered if a.local_path]
        duration = self.concatenator(paths, output_path)
        final_ref = storage.persist_file(output_path, out_dir, "final_video.mp4")

        with Session(self.engine) as session:
            EpisodeRepo(session).set_final(episode_id, final_ref, duration)
        return final_ref

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

        from ....features.compositing.adventure_compositor import (
            RoundAssets,
            compose_narrated_segment,
            compose_round,
        )
        from ....features.scripting.adventure import AdventureScript
        from ....features.transcription.whisper import WhisperTranscriber
        from ...db.repositories import ScriptRepo

        with Session(self.engine) as session:
            episode = EpisodeRepo(session).get(episode_id)
            if episode is None:
                raise ValueError(f"episode {episode_id} not found")
            project = ProjectRepo(session).get(episode.project_id)
            project_name = project.name if project else f"project_{episode.project_id}"
            assets = AssetRepo(session).assets_by_episode(episode_id)
            row = ScriptRepo(session).latest_for_episode(episode_id)

        if row is None:
            logger.warning(
                "assemble_rich(ep=%s): pas de script → repli sur concat simple "
                "(les assets riches narration/choix/timer NE seront PAS montés)",
                episode_id,
            )
            return self.assemble(episode_id)
        try:
            script = AdventureScript.model_validate_json(row.script_json)
        except Exception as exc:
            logger.warning(
                "assemble_rich(ep=%s): script invalide (%s) → repli concat simple",
                episode_id, exc,
            )
            return self.assemble(episode_id)

        # (round_index, beat) -> local file (materialized), present AND not écarté.
        by_key = {
            (a.round_index, a.beat): storage.materialize(a.local_path)
            for a in assets
            if a.local_path and storage.exists(a.local_path) and not a.excluded
        }

        def g(ri: int | None, beat: str) -> str | None:
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
            missing = [b for b in req_video_beats if g(ri, b) is None]
            if missing:
                logger.warning(
                    "assemble_rich(ep=%s): round %s incomplet, beats manquants %s "
                    "→ repli concat simple (montage riche abandonné)",
                    episode_id, ri, missing,
                )
                return self.assemble(episode_id)

        # Rich compositing (MoviePy). On any failure (e.g. unreadable media in
        # offline tests), degrade gracefully to the simple concat.
        try:
            round_files: list[str] = []
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
                        fatal_choice_index=(
                            0 if script.rounds[ri].choices[0].is_fatal else 1
                        ),
                    ),
                    follower, transcriber, rf, workdir=work,
                )
                round_files.append(rf)

            epi_video = g(None, "epilogue.motion")
            if epi_video:
                ef = os.path.join(work, "epilogue.mp4")
                compose_narrated_segment(
                    epi_video,
                    g(None, "epilogue.narration") or "",
                    transcriber, ef, workdir=work,
                )
                round_files.append(ef)

            # P4 — segment d'entrée « Si tu as choisi {nom} » : zoom sur le
            # compagnon (réf perso) pendant la narration de transition.
            entry_prev = g(None, "intro")  # la vidéo qui précède l'entrée (intro)
            entry_img = g(None, "char_reference")  # repli si pas d'intro
            entry_narr = g(None, "transition.narration")
            if entry_narr and (entry_prev or entry_img):
                from ....features.compositing.adventure_compositor import (
                    compose_entry_segment,
                )

                entry = os.path.join(work, "entry.mp4")
                compose_entry_segment(
                    entry_prev or "", entry_narr, transcriber, entry, work,
                    fallback_image=entry_img or "",
                )
                round_files.insert(0, entry)

            # Intro (système historique) tout en TÊTE si elle a été générée.
            intro = g(None, "intro")
            if intro:
                round_files.insert(0, intro)

            output_path = os.path.join(out_dir, "final_video.mp4")
            duration = self.concatenator(round_files, output_path)
            final_ref = storage.persist_file(output_path, out_dir, "final_video.mp4")
        except Exception as exc:
            logger.warning(
                "assemble_rich(ep=%s): échec du compositing riche (%s) → repli "
                "concat simple", episode_id, exc,
            )
            return self.assemble(episode_id)

        with Session(self.engine) as session:
            EpisodeRepo(session).set_final(episode_id, final_ref, duration)
        return final_ref
