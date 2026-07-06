"""Typed repositories over the VCM Studio tables.

Each repo wraps a :class:`~sqlmodel.Session` and exposes CRUD plus a few useful
queries (``assets_by_episode``, ``cost_total_by_episode``...). Callers own the
session lifecycle (commit happens inside the mutating methods).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, select

from src.studio.db.models import (
    AdventureScriptRow,
    AppSetting,
    Asset,
    CostEntry,
    EditorDocumentRow,
    Episode,
    GenerationJob,
    Project,
    PromptTemplate,
    Template,
    User,
    UserApiKey,
    VoiceProfile,
)


class ProjectRepo:
    """CRUD for :class:`Project`."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        name: str,
        settings_json: str | None = None,
        owner_id: int | None = None,
    ) -> Project:
        project = Project(
            name=name, settings_json=settings_json, owner_id=owner_id
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get(self, project_id: int) -> Project | None:
        return self.session.get(Project, project_id)

    def get_by_name(self, name: str) -> Project | None:
        return self.session.exec(
            select(Project).where(Project.name == name)
        ).first()

    def list(self) -> Sequence[Project]:
        return self.session.exec(select(Project)).all()

    def list_for_owner(self, owner_id: int) -> Sequence[Project]:
        """Projets d'un utilisateur (B.2 isolation). L'admin utilise ``list``."""
        return self.session.exec(
            select(Project).where(Project.owner_id == owner_id)
        ).all()

    def delete(self, project_id: int) -> bool:
        project = self.get(project_id)
        if project is None:
            return False
        self.session.delete(project)
        self.session.commit()
        return True


class TemplateRepo:
    """CRUD pour :class:`Template` (bibliothèque de structures réutilisables)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, name: str, structure_json: str, owner_id: int | None = None
    ) -> Template:
        row = Template(name=name, structure_json=structure_json, owner_id=owner_id)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, template_id: int) -> Template | None:
        return self.session.get(Template, template_id)

    def list(self) -> Sequence[Template]:
        return self.session.exec(select(Template)).all()

    def list_for_owner(self, owner_id: int) -> Sequence[Template]:
        return self.session.exec(
            select(Template).where(Template.owner_id == owner_id)
        ).all()

    def save(
        self, template_id: int, structure_json: str, name: str | None = None
    ) -> Template | None:
        row = self.get(template_id)
        if row is None:
            return None
        row.structure_json = structure_json
        if name is not None:
            row.name = name
        row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, template_id: int) -> bool:
        row = self.get(template_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.commit()
        return True


class PromptTemplateRepo:
    """CRUD pour :class:`PromptTemplate` (bibliothèque de prompts système)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, name: str, identity: str, roles_json: str, owner_id: int | None = None
    ) -> PromptTemplate:
        row = PromptTemplate(
            name=name, identity=identity, roles_json=roles_json, owner_id=owner_id
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, template_id: int) -> PromptTemplate | None:
        return self.session.get(PromptTemplate, template_id)

    def list(self) -> Sequence[PromptTemplate]:
        return self.session.exec(select(PromptTemplate)).all()

    def list_for_owner(self, owner_id: int) -> Sequence[PromptTemplate]:
        return self.session.exec(
            select(PromptTemplate).where(PromptTemplate.owner_id == owner_id)
        ).all()

    def save(
        self,
        template_id: int,
        identity: str,
        roles_json: str,
        name: str | None = None,
    ) -> PromptTemplate | None:
        row = self.get(template_id)
        if row is None:
            return None
        row.identity = identity
        row.roles_json = roles_json
        if name is not None:
            row.name = name
        row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, template_id: int) -> bool:
        row = self.get(template_id)
        if row is None:
            return False
        self.session.delete(row)
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
        theme: str = "horror",
    ) -> Episode:
        episode = Episode(
            project_id=project_id,
            title=title,
            status=status,
            format=format,
            draft_mode=draft_mode,
            theme=theme,
        )
        self.session.add(episode)
        self.session.commit()
        self.session.refresh(episode)
        return episode

    def get(self, episode_id: int) -> Episode | None:
        return self.session.get(Episode, episode_id)

    def list(self) -> Sequence[Episode]:
        return self.session.exec(select(Episode)).all()

    def by_project(self, project_id: int) -> Sequence[Episode]:
        return self.session.exec(
            select(Episode).where(Episode.project_id == project_id)
        ).all()

    def by_owner(self, owner_id: int) -> Sequence[Episode]:
        """Épisodes des projets d'un utilisateur (B.2 isolation, join Project)."""
        return self.session.exec(
            select(Episode)
            .join(Project, Episode.project_id == Project.id)  # type: ignore[arg-type]
            .where(Project.owner_id == owner_id)
        ).all()

    def update_status(self, episode_id: int, status: str) -> Episode | None:
        episode = self.get(episode_id)
        if episode is None:
            return None
        episode.status = status
        self.session.add(episode)
        self.session.commit()
        self.session.refresh(episode)
        return episode

    def set_final(
        self, episode_id: int, final_path: str, duration_s: float | None = None
    ) -> Episode | None:
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

    def set_brief(self, episode_id: int, brief_json: str) -> Episode | None:
        """Persiste le brief du producteur (JSON `Brief`) sur l'épisode."""
        episode = self.get(episode_id)
        if episode is None:
            return None
        episode.brief_json = brief_json
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

    def get(self, script_id: int) -> AdventureScriptRow | None:
        return self.session.get(AdventureScriptRow, script_id)

    def latest_for_episode(
        self, episode_id: int
    ) -> AdventureScriptRow | None:
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
        round_index: int | None = None,
        prompt: str | None = None,
        local_path: str | None = None,
        status: str = "pending",
        draft: bool = True,
        sha: str | None = None,
        editor_document_id: int | None = None,
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
            editor_document_id=editor_document_id,
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def get(self, asset_id: int) -> Asset | None:
        return self.session.get(Asset, asset_id)

    def assets_by_episode(
        self, episode_id: int, kind: str | None = None
    ) -> Sequence[Asset]:
        statement = select(Asset).where(Asset.episode_id == episode_id)
        if kind is not None:
            statement = statement.where(Asset.kind == kind)
        return self.session.exec(statement).all()

    def assets_by_document(
        self, editor_document_id: int
    ) -> Sequence[Asset]:
        """E5 : tous les assets générés pour un document de l'éditeur."""
        return self.session.exec(
            select(Asset).where(
                Asset.editor_document_id == editor_document_id
            )
        ).all()

    def by_document_and_beat(
        self, editor_document_id: int, beat: str
    ) -> Asset | None:
        """E5 : l'asset d'une brique donnée (beat == brick id) dans un document."""
        return self.session.exec(
            select(Asset)
            .where(Asset.editor_document_id == editor_document_id)
            .where(Asset.beat == beat)
            .order_by(Asset.id.desc())  # type: ignore[union-attr]
        ).first()

    def update(
        self,
        asset_id: int,
        prompt: str | None = None,
        excluded: bool | None = None,
    ) -> Asset | None:
        """Édite le prompt et/ou le flag `excluded` d'un asset (M1).

        Seuls les champs non-None sont modifiés (None = inchangé).
        """
        asset = self.get(asset_id)
        if asset is None:
            return None
        if prompt is not None:
            asset.prompt = prompt
        if excluded is not None:
            asset.excluded = excluded
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset

    def set_local_path(
        self, asset_id: int, local_path: str, sha: str | None = None
    ) -> Asset | None:
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
        prediction_id: str | None = None,
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

    def get(self, job_id: int) -> GenerationJob | None:
        return self.session.get(GenerationJob, job_id)

    def mark_done(
        self, job_id: int, duration_s: float | None = None
    ) -> GenerationJob | None:
        return self._set_status(job_id, "done", duration_s=duration_s)

    def mark_failed(
        self, job_id: int, error: str
    ) -> GenerationJob | None:
        return self._set_status(job_id, "failed", error=error)

    def _set_status(
        self,
        job_id: int,
        status: str,
        duration_s: float | None = None,
        error: str | None = None,
    ) -> GenerationJob | None:
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
        registre: str | None = None,
        description: str | None = None,
        voice_id: str | None = None,
        sample_path: str | None = None,
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

    def get(self, voice_id: int) -> VoiceProfile | None:
        return self.session.get(VoiceProfile, voice_id)

    def get_by_name(self, name: str) -> VoiceProfile | None:
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
        source: str = "estimate",
        predict_time_s: float | None = None,
    ) -> CostEntry:
        entry = CostEntry(
            job_id=job_id,
            model=model,
            amount_usd=amount_usd,
            units=units,
            unit_kind=unit_kind,
            source=source,
            is_estimate=(source == "estimate"),
            predict_time_s=predict_time_s,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def get(self, entry_id: int) -> CostEntry | None:
        return self.session.get(CostEntry, entry_id)

    def total(self) -> float:
        """Sum of all cost entries in USD."""
        entries = self.session.exec(select(CostEntry)).all()
        return float(sum(e.amount_usd for e in entries))

    def cost_total_by_episode(self, episode_id: int) -> float:
        """Total USD spent on an episode, joining CostEntry -> Job -> Asset."""
        return float(sum(e["amount_usd"] for e in self.actual_by_episode(episode_id)))

    def actual_by_episode(self, episode_id: int) -> list[dict[str, Any]]:
        """Per-node ACTUAL cost rows for an episode (CostEntry ⋈ Job ⋈ Asset)."""
        statement = (
            select(CostEntry, Asset)
            .join(GenerationJob, GenerationJob.id == CostEntry.job_id)  # type: ignore[arg-type]
            .join(Asset, Asset.id == GenerationJob.asset_id)  # type: ignore[arg-type]
            .where(Asset.episode_id == episode_id)
        )
        rows = self.session.exec(statement).all()
        return [
            {
                "asset_id": a.id,
                "beat": a.beat,
                "kind": a.kind,
                "model": c.model,
                "amount_usd": round(c.amount_usd, 6),
                "units": c.units,
                "unit_kind": c.unit_kind,
                "source": c.source,
                "is_estimate": c.is_estimate,
            }
            for c, a in rows
        ]


class EditorDocRepo:
    """CRUD for :class:`EditorDocumentRow` (E5) plus per-project listing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        project_id: int,
        title: str,
        doc_json: str,
        episode_id: int | None = None,
        schema_version: int = 1,
    ) -> EditorDocumentRow:
        row = EditorDocumentRow(
            project_id=project_id,
            title=title,
            doc_json=doc_json,
            episode_id=episode_id,
            schema_version=schema_version,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, doc_id: int) -> EditorDocumentRow | None:
        return self.session.get(EditorDocumentRow, doc_id)

    def by_project(self, project_id: int) -> Sequence[EditorDocumentRow]:
        return self.session.exec(
            select(EditorDocumentRow).where(
                EditorDocumentRow.project_id == project_id
            )
        ).all()

    def by_episode(self, episode_id: int) -> EditorDocumentRow | None:
        """Le document éditable le plus RÉCENT d'un épisode (None si aucun).

        Sert à router l'ouverture d'un épisode vers sa revue par scènes plutôt que
        vers l'ancienne page script (le plus récent l'emporte s'il y en a plusieurs).
        """
        return self.session.exec(
            select(EditorDocumentRow)
            .where(EditorDocumentRow.episode_id == episode_id)
            .order_by(EditorDocumentRow.id.desc())  # type: ignore[union-attr]
        ).first()

    def by_owner(self, owner_id: int) -> Sequence[EditorDocumentRow]:
        """Documents des projets d'un utilisateur (B.2 isolation, join Project)."""
        return self.session.exec(
            select(EditorDocumentRow)
            .join(Project, EditorDocumentRow.project_id == Project.id)  # type: ignore[arg-type]
            .where(Project.owner_id == owner_id)
        ).all()

    def list(self) -> Sequence[EditorDocumentRow]:
        return self.session.exec(select(EditorDocumentRow)).all()

    def save(
        self,
        doc_id: int,
        doc_json: str,
        title: str | None = None,
        schema_version: int | None = None,
    ) -> EditorDocumentRow | None:
        """Update the stored ``doc_json`` (and optionally title/version)."""
        row = self.get(doc_id)
        if row is None:
            return None
        row.doc_json = doc_json
        if title is not None:
            row.title = title
        if schema_version is not None:
            row.schema_version = schema_version
        row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def delete(self, doc_id: int) -> bool:
        row = self.get(doc_id)
        if row is None:
            return False
        self.session.delete(row)
        self.session.commit()
        return True

    def set_distribution(
        self, doc_id: int, distribution_json: str
    ) -> EditorDocumentRow | None:
        """Persiste la fiche de sortie (JSON `DistributionKit`) sur le document."""
        row = self.get(doc_id)
        if row is None:
            return None
        row.distribution_json = distribution_json
        row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row


class UserRepo:
    """CRUD for :class:`User` (auth Phase B)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, email: str, password_hash: str, is_admin: bool = False
    ) -> User:
        user = User(
            email=email, password_hash=password_hash, is_admin=is_admin
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.exec(
            select(User).where(User.email == email)
        ).first()

    def count(self) -> int:
        return len(self.session.exec(select(User)).all())


class UserApiKeyRepo:
    """Clés API chiffrées par utilisateur (B.2). Une ligne par (user, provider)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _get_row(self, user_id: int, provider: str) -> UserApiKey | None:
        return self.session.exec(
            select(UserApiKey).where(
                UserApiKey.user_id == user_id,
                UserApiKey.provider == provider,
            )
        ).first()

    def get(self, user_id: int, provider: str) -> UserApiKey | None:
        return self._get_row(user_id, provider)

    def upsert(self, user_id: int, provider: str, ciphertext: str) -> None:
        row = self._get_row(user_id, provider)
        if row is None:
            row = UserApiKey(
                user_id=user_id, provider=provider, ciphertext=ciphertext
            )
        else:
            row.ciphertext = ciphertext
            row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()

    def status(self, user_id: int) -> dict[str, bool]:
        rows = self.session.exec(
            select(UserApiKey).where(UserApiKey.user_id == user_id)
        ).all()
        return {r.provider: True for r in rows}


class SettingRepo:
    """CRUD for :class:`AppSetting` (generic key/value, incl. BYOK API keys)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str) -> str | None:
        row = self.session.get(AppSetting, key)
        return row.value if row else None

    def set(self, key: str, value: str) -> None:
        row = self.session.get(AppSetting, key)
        if row is None:
            row = AppSetting(key=key, value=value)
        else:
            row.value = value
            row.updated_at = datetime.now(UTC)
        self.session.add(row)
        self.session.commit()
