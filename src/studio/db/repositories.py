"""Typed repositories over the VCM Studio tables.

Each repo wraps a :class:`~sqlmodel.Session` and exposes CRUD plus a few useful
queries (``assets_by_episode``, ``cost_total_by_episode``...). Callers own the
session lifecycle (commit happens inside the mutating methods).
"""

from __future__ import annotations

from typing import Optional, Sequence

from sqlmodel import Session, select

from src.studio.db.models import (
    AdventureScriptRow,
    Asset,
    CostEntry,
    Episode,
    GenerationJob,
    Project,
    VoiceProfile,
)


class ProjectRepo:
    """CRUD for :class:`Project`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, name: str, settings_json: Optional[str] = None) -> Project:
        project = Project(name=name, settings_json=settings_json)
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get(self, project_id: int) -> Optional[Project]:
        return self.session.get(Project, project_id)

    def get_by_name(self, name: str) -> Optional[Project]:
        return self.session.exec(
            select(Project).where(Project.name == name)
        ).first()

    def list(self) -> Sequence[Project]:
        return self.session.exec(select(Project)).all()

    def delete(self, project_id: int) -> bool:
        project = self.get(project_id)
        if project is None:
            return False
        self.session.delete(project)
        self.session.commit()
        return True


class EpisodeRepo:
    """CRUD for :class:`Episode` plus per-project listing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        project_id: int,
        title: str,
        status: str = "draft",
        format: str = "aventure",
        draft_mode: bool = True,
    ) -> Episode:
        episode = Episode(
            project_id=project_id,
            title=title,
            status=status,
            format=format,
            draft_mode=draft_mode,
        )
        self.session.add(episode)
        self.session.commit()
        self.session.refresh(episode)
        return episode

    def get(self, episode_id: int) -> Optional[Episode]:
        return self.session.get(Episode, episode_id)

    def list(self) -> Sequence[Episode]:
        return self.session.exec(select(Episode)).all()

    def by_project(self, project_id: int) -> Sequence[Episode]:
        return self.session.exec(
            select(Episode).where(Episode.project_id == project_id)
        ).all()

    def update_status(self, episode_id: int, status: str) -> Optional[Episode]:
        episode = self.get(episode_id)
        if episode is None:
            return None
        episode.status = status
        self.session.add(episode)
        self.session.commit()
        self.session.refresh(episode)
        return episode

    def set_final(
        self, episode_id: int, final_path: str, duration_s: Optional[float] = None
    ) -> Optional[Episode]:
        episode = self.get(episode_id)
        if episode is None:
            return None
        episode.final_path = final_path
        if duration_s is not None:
            episode.duration_s = duration_s
        episode.status = "done"
        self.session.add(episode)
        self.session.commit()
        self.session.refresh(episode)
        return episode

    def delete(self, episode_id: int) -> bool:
        episode = self.get(episode_id)
        if episode is None:
            return False
        self.session.delete(episode)
        self.session.commit()
        return True


class ScriptRepo:
    """CRUD for :class:`AdventureScriptRow`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, episode_id: int, script_json: str, edited: bool = False
    ) -> AdventureScriptRow:
        row = AdventureScriptRow(
            episode_id=episode_id, script_json=script_json, edited=edited
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, script_id: int) -> Optional[AdventureScriptRow]:
        return self.session.get(AdventureScriptRow, script_id)

    def latest_for_episode(
        self, episode_id: int
    ) -> Optional[AdventureScriptRow]:
        return self.session.exec(
            select(AdventureScriptRow)
            .where(AdventureScriptRow.episode_id == episode_id)
            .order_by(AdventureScriptRow.id.desc())  # type: ignore[union-attr]
        ).first()


class AssetRepo:
    """CRUD for :class:`Asset` plus episode-scoped queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        episode_id: int,
        beat: str,
        kind: str,
        round_index: Optional[int] = None,
        prompt: Optional[str] = None,
        local_path: Optional[str] = None,
        status: str = "pending",
        draft: bool = True,
        sha: Optional[str] = None,
    ) -> Asset:
        asset = Asset(
            episode_id=episode_id,
            beat=beat,
            kind=kind,
            round_index=round_index,
            prompt=prompt,
            local_path=local_path,
            status=status,
            draft=draft,
            sha=sha,
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: int) -> Optional[Asset]:
        return self.session.get(Asset, asset_id)

    def assets_by_episode(
        self, episode_id: int, kind: Optional[str] = None
    ) -> Sequence[Asset]:
        statement = select(Asset).where(Asset.episode_id == episode_id)
        if kind is not None:
            statement = statement.where(Asset.kind == kind)
        return self.session.exec(statement).all()

    def set_local_path(
        self, asset_id: int, local_path: str, sha: Optional[str] = None
    ) -> Optional[Asset]:
        """Record the downloaded on-disk path (never a replicate.delivery URL)."""
        asset = self.get(asset_id)
        if asset is None:
            return None
        asset.local_path = local_path
        asset.status = "ready"
        if sha is not None:
            asset.sha = sha
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def delete(self, asset_id: int) -> bool:
        asset = self.get(asset_id)
        if asset is None:
            return False
        self.session.delete(asset)
        self.session.commit()
        return True


class JobRepo:
    """CRUD for :class:`GenerationJob`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        asset_id: int,
        model: str,
        prediction_id: Optional[str] = None,
        status: str = "pending",
    ) -> GenerationJob:
        job = GenerationJob(
            asset_id=asset_id,
            model=model,
            prediction_id=prediction_id,
            status=status,
        )
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get(self, job_id: int) -> Optional[GenerationJob]:
        return self.session.get(GenerationJob, job_id)

    def mark_done(
        self, job_id: int, duration_s: Optional[float] = None
    ) -> Optional[GenerationJob]:
        return self._set_status(job_id, "done", duration_s=duration_s)

    def mark_failed(
        self, job_id: int, error: str
    ) -> Optional[GenerationJob]:
        return self._set_status(job_id, "failed", error=error)

    def _set_status(
        self,
        job_id: int,
        status: str,
        duration_s: Optional[float] = None,
        error: Optional[str] = None,
    ) -> Optional[GenerationJob]:
        job = self.get(job_id)
        if job is None:
            return None
        job.status = status
        if duration_s is not None:
            job.duration_s = duration_s
        if error is not None:
            job.error = error
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job


class VoiceRepo:
    """CRUD for :class:`VoiceProfile` (the voice bank)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        name: str,
        registre: Optional[str] = None,
        description: Optional[str] = None,
        voice_id: Optional[str] = None,
        sample_path: Optional[str] = None,
    ) -> VoiceProfile:
        voice = VoiceProfile(
            name=name,
            registre=registre,
            description=description,
            voice_id=voice_id,
            sample_path=sample_path,
        )
        self.session.add(voice)
        self.session.commit()
        self.session.refresh(voice)
        return voice

    def get(self, voice_id: int) -> Optional[VoiceProfile]:
        return self.session.get(VoiceProfile, voice_id)

    def get_by_name(self, name: str) -> Optional[VoiceProfile]:
        return self.session.exec(
            select(VoiceProfile).where(VoiceProfile.name == name)
        ).first()

    def list(self) -> Sequence[VoiceProfile]:
        return self.session.exec(select(VoiceProfile)).all()

    def delete(self, voice_id: int) -> bool:
        voice = self.get(voice_id)
        if voice is None:
            return False
        self.session.delete(voice)
        self.session.commit()
        return True


class CostRepo:
    """CRUD for :class:`CostEntry` plus aggregate cost queries."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        job_id: int,
        model: str,
        amount_usd: float,
        units: float = 0.0,
        unit_kind: str = "units",
    ) -> CostEntry:
        entry = CostEntry(
            job_id=job_id,
            model=model,
            amount_usd=amount_usd,
            units=units,
            unit_kind=unit_kind,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def get(self, entry_id: int) -> Optional[CostEntry]:
        return self.session.get(CostEntry, entry_id)

    def total(self) -> float:
        """Sum of all cost entries in USD."""
        entries = self.session.exec(select(CostEntry)).all()
        return float(sum(e.amount_usd for e in entries))

    def cost_total_by_episode(self, episode_id: int) -> float:
        """Total USD spent on an episode, joining CostEntry -> Job -> Asset."""
        statement = (
            select(CostEntry)
            .join(GenerationJob, GenerationJob.id == CostEntry.job_id)  # type: ignore[arg-type]
            .join(Asset, Asset.id == GenerationJob.asset_id)  # type: ignore[arg-type]
            .where(Asset.episode_id == episode_id)
        )
        entries = self.session.exec(statement).all()
        return float(sum(e.amount_usd for e in entries))
