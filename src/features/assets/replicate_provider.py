"""Replicate-based asset generation."""

from typing import Optional
import replicate
from .ports import AssetProvider


class ReplicateAssetProvider(AssetProvider):
    """Generate assets using Replicate AI models."""

    def synthesize_voice(self, text: str, voice_id: str) -> str:
        """Synthesize voice using Minimax Speech model."""
        result = replicate.run(
            "minimax/speech-2.8-turbo",
            input={
                "text": text,
                "voice_id": voice_id,
            },
        )
        return str(result)

    def generate_image(self, prompt: str, size: str, aspect_ratio: str) -> str:
        """Generate image using ByteDance SeedDream model."""
        result = replicate.run(
            "bytedance/seedream-4.5",
            input={
                "prompt": prompt,
                "size": size,
                "aspect_ratio": aspect_ratio,
            },
        )
        # Result is a list, take first element
        return str(result[0])

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
        """Generate animated video using Pruna P-Video model."""
        params = {
            "prompt": prompt,
            "image": image_url,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "draft": draft,
            "save_audio": True,
        }
        if audio_url:
            params["audio"] = audio_url

        result = replicate.run("prunaai/p-video", input=params)
        return str(result)
