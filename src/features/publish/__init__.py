"""Feature PUBLICATION — poster le MP4 rendu sur la plateforme (dernier maillon endgame)."""

from .fake_publisher import FakePublisher
from .model import PublishResult
from .ports import DEFAULT_PLATFORM, Publisher, PublishError

__all__ = [
    "DEFAULT_PLATFORM",
    "FakePublisher",
    "PublishError",
    "PublishResult",
    "Publisher",
]
