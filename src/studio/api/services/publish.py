"""Publish service — poster une vidéo rendue (le dernier maillon).

Fake par défaut (offline) ; l'impl réelle (API plateforme) est un swap dès que les
credentials sont configurés — même patron que les autres factories."""

from __future__ import annotations

from ....features.publish import (
    DEFAULT_PLATFORM,
    FakePublisher,
    Publisher,
    PublishError,
    PublishResult,
)


def get_publisher() -> Publisher:
    """Le publisher actif (Fake tant que l'API plateforme n'est pas câblée)."""
    return FakePublisher()


def publish_video(
    video_ref: str,
    *,
    platform: str = DEFAULT_PLATFORM,
    caption: str = "",
    publisher: Publisher | None = None,
) -> PublishResult:
    """Publie une vidéo (référence = chemin/URL du MP4 rendu). Lève si vide."""
    if not video_ref.strip():
        raise PublishError("aucune vidéo à publier (rends d'abord le MP4).")
    pub = publisher or get_publisher()
    return pub.publish(video_ref, platform=platform, caption=caption)
