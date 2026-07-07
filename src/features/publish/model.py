"""Modèles de PUBLICATION — le dernier maillon (poster le MP4 sur la plateforme)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublishResult(_M):
    """Le résultat d'une publication (réelle ou simulée)."""

    platform: str                 # tiktok / reels / shorts
    status: str = "published"     # published / scheduled / failed
    published_id: str = ""        # id de la publication chez la plateforme
    url: str = ""                 # URL publique (si disponible)
