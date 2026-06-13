"""Asset generation service — image-first, local download, DB + cost tracking.

Executes a `plan_episode_assets` plan against an `AssetProvider` (real Replicate
or the FakeAssetProvider in tests). For every asset it:
  1. creates an Asset row (status pending),
  2. calls the provider (image -> then its motion video; audio standalone),
  3. downloads the output to exports/ IMMEDIATELY (never store the expiring URL),
  4. records a GenerationJob + CostEntry,
  5. publishes SSE progress events.

The provider and the downloader are injected so tests run fully offline with no
network and no real files.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....features.assets.ports import AssetProvider
from ....features.assets.replicate_provider import ReplicateAssetProvider
from ....features.scripting.adventure import AdventureScript
from ...db.repositories import AssetRepo, CostRepo, EpisodeRepo, JobRepo
from ..events import bus
from . import pricing
from .generation_plan import PlannedAsset, plan_episode_assets

# Default voice ids (mirror Pipeline.generate_assets: narrator vs character).
NARRATOR_VOICE_ID = "Deep_Voice_Man"
CHARACTER_VOICE_ID = "Deep_Voice_Man"

# Signature: (url, folder, filename) -> local path or None.
Downloader = Callable[[str, str, str], Optional[str]]


def _default_downloader(url: str, folder: str, filename: str) -> Optional[str]:
    from ....infra.download import download_file

    return download_file(url, folder, filename)


def _ext_for(kind: str) -> str:
    return {"image": "png", "video": "mp4", "audio": "mp3"}[kind]


def _filename(asset: PlannedAsset) -> str:
    """Stable on-disk filename for a planned asset (round + beat + kind)."""
    prefix = "epi" if asset.round_index is None else f"r{asset.round_index}"
    safe_beat = asset.beat.replace(".", "_")
    return f"{prefix}_{safe_beat}.{_ext_for(asset.kind)}"


class AssetGenerationService:
    """Runs the image-first generation plan for an episode and persists results."""

    def __init__(
        self,
        engine: Engine,
        provider: Optional[AssetProvider] = None,
        downloader: Optional[Downloader] = None,
    ) -> None:
        self.engine = engine
        self.provider = provider or ReplicateAssetProvider()
        self.downloader = downloader or _default_downloader

    def export_dir(self, project_name: str, episode_id: int) -> str:
        return os.path.join("exports", project_name, f"episode_{episode_id}")

    def generate_episode(
        self, episode_id: int, script: AdventureScript, side: str = "left"
    ) -> None:
        """Generate every asset of an episode (blocking; run in a background task)."""
        with Session(self.engine) as session:
            episode = EpisodeRepo(session).get(episode_id)
            if episode is None:
                raise ValueError(f"episode {episode_id} not found")
            from ...db.repositories import ProjectRepo

            project = ProjectRepo(session).get(episode.project_id)
            project_name = project.name if project else f"project_{episode.project_id}"
            draft = episode.draft_mode

        plan = plan_episode_assets(script, side)  # type: ignore[arg-type]
        out_dir = self.export_dir(project_name, episode_id)
        os.makedirs(out_dir, exist_ok=True)

        bus.publish(episode_id, {"type": "generation_started", "total": len(plan)})

        # Image URLs are remembered within this run so a *.motion video can reuse
        # the *.frame image it was generated from (image-first).
        frame_url_by_beat: dict[str, str] = {}

        for index, planned in enumerate(plan):
            self._generate_one(
                episode_id, planned, out_dir, draft, frame_url_by_beat, index
            )

        with Session(self.engine) as session:
            EpisodeRepo(session).update_status(episode_id, "assets")
        bus.publish(episode_id, {"type": "generation_done", "total": len(plan)})

    def _generate_one(
        self,
        episode_id: int,
        planned: PlannedAsset,
        out_dir: str,
        draft: bool,
        frame_url_by_beat: dict[str, str],
        index: int,
    ) -> None:
        with Session(self.engine) as session:
            asset_repo = AssetRepo(session)
            job_repo = JobRepo(session)
            cost_repo = CostRepo(session)

            prompt = planned.motion_prompt or planned.image_prompt or planned.text
            asset = asset_repo.create(
                episode_id=episode_id,
                beat=planned.beat,
                kind=planned.kind,
                round_index=planned.round_index,
                prompt=prompt,
                draft=draft,
                status="generating",
            )
            assert asset.id is not None  # set by the DB on commit
            asset_id = asset.id
            bus.publish(
                episode_id,
                {
                    "type": "asset_started",
                    "asset_id": asset_id,
                    "beat": planned.beat,
                    "kind": planned.kind,
                    "index": index,
                },
            )

            model, url, cost_line = self._call_provider(
                planned, draft, frame_url_by_beat
            )
            job = job_repo.create(asset_id, model, status="running")
            assert job.id is not None
            job_id = job.id

            try:
                local = self.downloader(url, out_dir, _filename(planned)) if url else None
            except Exception as exc:  # download failure -> mark job failed
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    episode_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return

            asset_repo.set_local_path(asset_id, local or "")
            job_repo.mark_done(job_id)
            cost_repo.create(
                job_id,
                cost_line.model,
                cost_line.amount_usd,
                units=cost_line.units,
                unit_kind=cost_line.unit_kind,
            )
            bus.publish(
                episode_id,
                {
                    "type": "asset_ready",
                    "asset_id": asset_id,
                    "local_path": local,
                    "amount_usd": cost_line.amount_usd,
                },
            )

    def _call_provider(
        self,
        planned: PlannedAsset,
        draft: bool,
        frame_url_by_beat: dict[str, str],
    ) -> tuple[str, str, pricing.CostLine]:
        """Dispatch to the right provider method; return (model, url, cost line)."""
        if planned.kind == "image":
            url = self.provider.generate_image(
                planned.image_prompt or "", "2K", "9:16"
            )
            frame_url_by_beat[planned.beat] = url
            return pricing.MODEL_IMAGE, url, pricing.image_cost(1)

        if planned.kind == "video":
            # Reuse the frame generated just before (image-first).
            frame_beat = planned.beat.replace(".motion", ".frame")
            image_url = frame_url_by_beat.get(frame_beat, "")
            url = self.provider.animate_video(
                planned.motion_prompt or "",
                image_url,
                duration=pricing.BEAT_VIDEO_SECONDS,
                aspect_ratio="9:16",
                resolution="720p",
                draft=draft,
            )
            return (
                pricing.MODEL_VIDEO,
                url,
                pricing.video_cost(pricing.BEAT_VIDEO_SECONDS, draft=draft),
            )

        # audio
        voice_id = (
            NARRATOR_VOICE_ID if planned.beat == "narration" else CHARACTER_VOICE_ID
        )
        text = planned.text or ""
        url = self.provider.synthesize_voice(text, voice_id)
        return pricing.MODEL_VOICE, url, pricing.voice_cost(len(text))


def regenerate_asset(
    engine: Engine,
    asset_id: int,
    provider: Optional[AssetProvider] = None,
    downloader: Optional[Downloader] = None,
) -> Optional[int]:
    """Regenerate a single existing asset in place. Returns its episode id.

    Reuses the stored prompt. For a video asset it needs a source frame; if none
    is available it regenerates from an empty source (the provider handles it).
    """
    svc = AssetGenerationService(engine, provider=provider, downloader=downloader)
    with Session(engine) as session:
        asset = AssetRepo(session).get(asset_id)
        if asset is None:
            return None
        episode = EpisodeRepo(session).get(asset.episode_id)
        from ...db.repositories import ProjectRepo

        project = (
            ProjectRepo(session).get(episode.project_id) if episode else None
        )
        project_name = project.name if project else "project"
        episode_id = asset.episode_id
        planned = PlannedAsset(
            round_index=asset.round_index,
            beat=asset.beat,
            kind=asset.kind,  # type: ignore[arg-type]
            image_prompt=asset.prompt if asset.kind != "audio" else None,
            motion_prompt=asset.prompt if asset.kind == "video" else None,
            text=asset.prompt if asset.kind == "audio" else None,
        )
        draft = episode.draft_mode if episode else True

    out_dir = svc.export_dir(project_name, episode_id)
    os.makedirs(out_dir, exist_ok=True)
    svc._generate_one(episode_id, planned, out_dir, draft, {}, 0)
    return episode_id
