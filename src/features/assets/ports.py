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


@dataclass(frozen=True)
class RunResult:
    """Output of a metered model run + whatever real-cost signal the provider gave.

    ``cost_usd`` is the provider's billed amount when available (often absent);
    ``predict_time`` (seconds of compute, from ``metrics.predict_time``) lets us
    compute the real cost as ``predict_time × hardware_rate``. See cost_actual.py.
    """

    urls: List[str]
    cost_usd: Optional[float] = None
    predict_time: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None


class AssetProvider(Protocol):
    """Port for generating AI assets (voice, image, video)."""

    # The last metered run, stashed by run_model / the typed helpers so the
    # generation service can read the real cost without changing return types.
    last_run: Optional[RunResult]

    def run_model_metered(
        self, model_ref: str, params: Dict[str, Any]
    ) -> RunResult:
        """Run a model and return URLs + real-cost signal (cost/metrics)."""
        ...

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
