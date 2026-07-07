"""Publisher FAKE — déterministe, hors-ligne (dev + tests).

Ne poste rien : dérive un `published_id` stable du couple (plateforme, vidéo) et renvoie
un `PublishResult` « published ». Sert de défaut offline ; l'API réelle est un swap au bord."""

from __future__ import annotations

import re

from .model import PublishResult
from .ports import DEFAULT_PLATFORM


def _slug(ref: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", ref.lower())[-8:] or "clip"


class FakePublisher:
    """Implémente `Publisher` sans réseau (id déterministe, pas de post réel)."""

    def publish(
        self, video_ref: str, *, platform: str = DEFAULT_PLATFORM, caption: str = ""
    ) -> PublishResult:
        pid = f"{platform}_{_slug(video_ref)}"
        return PublishResult(
            platform=platform, status="published", published_id=pid,
            url=f"https://{platform}.example/{pid}",
        )
