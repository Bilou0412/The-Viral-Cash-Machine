"""Port de PUBLICATION (`typing.Protocol`) — poster une vidéo rendue sur une plateforme.

Impl Fake (offline/tests) ; l'impl réelle (API TikTok/Reels/Shorts) est un swap au bord,
dès que les credentials plateforme sont configurés."""

from __future__ import annotations

from typing import Protocol

from .model import PublishResult

DEFAULT_PLATFORM = "tiktok"


class PublishError(RuntimeError):
    """Échec de publication (vidéo absente, API plateforme injoignable…)."""


class Publisher(Protocol):
    def publish(
        self, video_ref: str, *, platform: str = DEFAULT_PLATFORM, caption: str = ""
    ) -> PublishResult: ...
