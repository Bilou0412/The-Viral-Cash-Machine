"""SQLModel tables for VCM Studio.

BLOBs live on disk (``exports/``); these tables hold only metadata, local paths
and Replicate prediction ids. Never store a ``replicate.delivery`` URL here — they
expire (see ``Asset.local_path`` / ``GenerationJob.prediction_id``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp used as the default for ``created_at``."""
    return datetime.now(timezone.utc)


class Project(SQLModel, table=True):
    """A project / channel grouping several episodes."""

    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    settings_json: Optional[str] = Field(default=None)


class Episode(SQLModel, table=True):
    """One Aventure video: lifecycle status, format, draft/final, final path."""

    __tablename__ = "episode"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    title: str
    # Lifecycle: draft -> assets -> montage -> done
    status: str = Field(default="draft", index=True)
    format: str = Field(default="aventure")
    draft_mode: bool = Field(default=True)
    duration_s: Optional[float] = Field(default=None)
    final_path: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class AdventureScriptRow(SQLModel, table=True):
    """The generated ``AdventureScript`` (serialized JSON) plus an edited flag."""

    __tablename__ = "adventure_script"

    id: Optional[int] = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="episode.id", index=True)
    script_json: str
    edited: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)


class Asset(SQLModel, table=True):
    """A single generated asset (image / video / audio).

    ``local_path`` is the on-disk path; the binary itself is never in the DB and a
    ``replicate.delivery`` URL is never stored.
    """

    __tablename__ = "asset"

    id: Optional[int] = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="episode.id", index=True)
    round_index: Optional[int] = Field(default=None)
    beat: str
    # One of: image / video / audio
    kind: str = Field(index=True)
    prompt: Optional[str] = Field(default=None)
    local_path: Optional[str] = Field(default=None)
    status: str = Field(default="pending")
    draft: bool = Field(default=True)
    sha: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class GenerationJob(SQLModel, table=True):
    """Tracks one Replicate generation backing an asset.

    Stores the durable ``prediction_id`` (not the expiring output URL).
    """

    __tablename__ = "generation_job"

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    model: str
    prediction_id: Optional[str] = Field(default=None)
    status: str = Field(default="pending", index=True)
    duration_s: Optional[float] = Field(default=None)
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class VoiceProfile(SQLModel, table=True):
    """Voice bank entry (migrated from ``assets/narrator_voice.json``).

    ``voice_id`` is durable (Replicate clone id, does not expire); ``sample_path``
    is a local audio sample.
    """

    __tablename__ = "voice_profile"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    registre: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    voice_id: Optional[str] = Field(default=None)
    sample_path: Optional[str] = Field(default=None)


class CostEntry(SQLModel, table=True):
    """Cost ledger row attached to a generation job."""

    __tablename__ = "cost_entry"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="generation_job.id", index=True)
    model: str
    units: float = Field(default=0.0)
    # What ``units`` counts: e.g. "seconds", "images", "characters"
    unit_kind: str = Field(default="units")
    amount_usd: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=_utcnow)
