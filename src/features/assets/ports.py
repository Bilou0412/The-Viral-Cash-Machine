"""Asset generation ports."""

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, Optional


@dataclass(frozen=True)
class AssetBundle:
    """Generated assets with URLs."""

    narrator_audio_url: Optional[str] = None
    character_audio_url: Optional[str] = None
    freeze_image_url: Optional[str] = None
    video_url: Optional[str] = None


class AssetProvider(Protocol):
    """Port for generating AI assets (voice, image, video)."""

    def synthesize_voice(
        self, text: str, voice_id: str, model: Optional[str] = None
    ) -> str:
        """Synthesize voice from text. Returns URL.

        `model` overrides the TTS model (e.g. a cloned voice needs the model it
        was cloned with). Default = the provider's standard model.
        """
        ...

    def generate_image(
        self,
        prompt: str,
        size: str,
        aspect_ratio: str,
        image_input: Optional[list[str]] = None,
    ) -> str:
        """Generate image from prompt. Returns URL.

        `image_input` : images de référence (image-to-image) pour garder un
        personnage/une DA cohérents d'une image à l'autre.
        """
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

    def run_model(self, model_ref: str, params: Dict[str, Any]) -> List[str]:
        """Run an arbitrary Replicate model with arbitrary params.

        Generic escape hatch for the video editor: any `owner/name` model ref
        plus an arbitrary `input` dict. Returns the normalized output URL(s).
        """
        ...
