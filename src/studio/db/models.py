"""SQLModel tables for VCM Studio.

BLOBs live on disk (``exports/``); these tables hold only metadata, local paths
and Replicate prediction ids. Never store a ``replicate.delivery`` URL here — they
expire (see ``Asset.local_path`` / ``GenerationJob.prediction_id``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp used as the default for ``created_at``."""
    return datetime.now(UTC)


class Project(SQLModel, table=True):
    """A project / channel grouping several episodes."""

    __tablename__ = "project"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    settings_json: str | None = Field(default=None)
    # Multi-tenant (B.2) : propriétaire du projet. Nullable pour les lignes legacy
    # (créées avant l'auth) → visibles uniquement des admins (ou backfillées).
    owner_id: int | None = Field(
        default=None, foreign_key="user.id", index=True
    )


class Episode(SQLModel, table=True):
    """One Aventure video: lifecycle status, format, draft/final, final path."""

    __tablename__ = "episode"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    title: str
    # Lifecycle: draft -> assets -> montage -> done
    status: str = Field(default="draft", index=True)
    format: str = Field(default="aventure")
    # DA / thème de l'épisode (cf. features.scripting.themes). Défaut « horror ».
    theme: str = Field(default="horror")
    draft_mode: bool = Field(default=True)
    duration_s: float | None = Field(default=None)
    final_path: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class AdventureScriptRow(SQLModel, table=True):
    """The generated ``AdventureScript`` (serialized JSON) plus an edited flag."""

    __tablename__ = "adventure_script"

    id: int | None = Field(default=None, primary_key=True)
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

    id: int | None = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="episode.id", index=True)
    round_index: int | None = Field(default=None)
    beat: str
    # One of: image / video / audio
    kind: str = Field(index=True)
    prompt: str | None = Field(default=None)
    local_path: str | None = Field(default=None)
    status: str = Field(default="pending")
    draft: bool = Field(default=True)
    # M1/M2 : asset écarté par l'auteur → exclu du montage (jamais supprimé).
    excluded: bool = Field(default=False)
    sha: str | None = Field(default=None)
    # E5 : asset issu d'une brique de l'éditeur timeline (None = asset Aventure).
    editor_document_id: int | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=_utcnow)


class GenerationJob(SQLModel, table=True):
    """Tracks one Replicate generation backing an asset.

    Stores the durable ``prediction_id`` (not the expiring output URL).
    """

    __tablename__ = "generation_job"

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id", index=True)
    model: str
    prediction_id: str | None = Field(default=None)
    status: str = Field(default="pending", index=True)
    duration_s: float | None = Field(default=None)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class VoiceProfile(SQLModel, table=True):
    """Voice bank entry (migrated from ``assets/narrator_voice.json``).

    ``voice_id`` is durable (Replicate clone id, does not expire); ``sample_path``
    is a local audio sample.
    """

    __tablename__ = "voice_profile"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    registre: str | None = Field(default=None)
    description: str | None = Field(default=None)
    voice_id: str | None = Field(default=None)
    sample_path: str | None = Field(default=None)


class EditorDocumentRow(SQLModel, table=True):
    """E5 : un document d'autoring de l'éditeur timeline, sérialisé en JSON.

    Le ``doc_json`` est un :class:`~src.editor.document.EditorDocument` dumpé ;
    il est ré-hydraté/migré via ``upgrade_document`` à la lecture. Versionné par
    ``schema_version`` pour les migrations futures.
    """

    __tablename__ = "editor_document"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    episode_id: int | None = Field(default=None, foreign_key="episode.id")
    title: str
    schema_version: int = Field(default=1)
    doc_json: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Template(SQLModel, table=True):
    """Un template réutilisable : la STRUCTURE d'une vidéo (le « contenant »).

    ``structure_json`` décrit les slots ordonnés (type vidéo/photo, durée, format,
    narration) SANS contenu — GPT le remplira ensuite (respect strict de la
    structure). Possédé directement par un utilisateur (bibliothèque de templates).
    """

    __tablename__ = "template"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    structure_json: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    owner_id: int | None = Field(default=None, foreign_key="user.id", index=True)


class CostEntry(SQLModel, table=True):
    """Cost ledger row attached to a generation job."""

    __tablename__ = "cost_entry"

    id: int | None = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="generation_job.id", index=True)
    model: str
    units: float = Field(default=0.0)
    # What ``units`` counts: e.g. "seconds", "images", "characters"
    unit_kind: str = Field(default="units")
    amount_usd: float = Field(default=0.0)
    # Provenance of amount_usd: "provider" (billed) | "compute" (predict_time ×
    # rate) | "estimate" (rate-card fallback). is_estimate flags non-real costs.
    source: str = Field(default="estimate")
    is_estimate: bool = Field(default=True)
    predict_time_s: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)


class User(SQLModel, table=True):
    """Compte utilisateur (auth Phase B).

    ``password_hash`` est un hash argon2 (jamais le mot de passe en clair).
    ``is_admin`` : en B.1 seul l'admin peut dépenser les clés globales ; en B.2
    chaque utilisateur aura ses propres clés (chiffrées) et pourra générer.
    """

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)


class UserApiKey(SQLModel, table=True):
    """Clé API d'un utilisateur, **chiffrée au repos** (Fernet) — B.2.

    ``ciphertext`` est le token Fernet (jamais la clé en clair). Une ligne par
    (utilisateur, provider). Remplace le stockage global ``AppSetting`` pour les
    clés : chaque utilisateur génère avec **ses** clés, à **ses** frais.
    """

    __tablename__ = "user_api_key"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    provider: str = Field(index=True)          # "openai" | "replicate"
    ciphertext: str
    updated_at: datetime = Field(default_factory=_utcnow)


class AppSetting(SQLModel, table=True):
    """Generic key/value app config — notably the BYOK API keys entered in the UI.

    Stored on the DB volume so they survive redeploys. Single-tenant (self-host):
    the value is the secret itself; per-user + encryption come with auth (Phase B/E).
    """

    __tablename__ = "app_setting"

    key: str = Field(primary_key=True)
    value: str = Field(default="")
    updated_at: datetime = Field(default_factory=_utcnow)
