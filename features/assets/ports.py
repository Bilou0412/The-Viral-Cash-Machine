"""Asset generation ports."""

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass(frozen=True)
class AssetBundle:
    """Generated assets with URLs."""

    narrator_audio_url: Optional[str] = None
    character_audio_url: Optional[str] = None
    freeze_image_url: Optional[str] = None
    video_url: Optional[str] = None


class AssetProvider(Protocol):
    """Port for generating AI assets (voice, image, video)."""

    def synthesize_voice(self, text: str, voice_id: str) -> str:
        """Synthesize voice from text. Returns URL."""
        ...

    def generate_image(self, prompt: str, size: str, aspect_ratio: str) -> str:
        """Generate image from prompt. Returns URL."""
        ...

    def animate_video(
        self,
        prompt: str,
        image_url: str,
        duration: float,
        aspect_ratio: str,
        resolution: str,
        audio_url: Optional[str] = None,
        draft: bool = False,
    ) -> str:
        """Generate animated video from image and prompt. Returns URL."""
        ...
