"""Offline test doubles for the studio API.

`FakeAssetProvider` satisfies the `AssetProvider` port without any network call:
it returns deterministic fake URLs and records every call, so tests can assert
the image-first ordering and counts. Used whenever tests exercise generation.
"""

from typing import Any

from ....features.assets.ports import AssetProvider, RunResult


class FakeAssetProvider(AssetProvider):
    """Records calls and returns deterministic fake asset URLs (no network)."""

    def __init__(self) -> None:
        self.voice_calls: list[tuple[str, str]] = []
        self.image_calls: list[tuple[str, str, str, list[str] | None]] = []
        self.video_calls: list[dict[str, object]] = []
        self.run_calls: list[tuple[str, dict[str, Any]]] = []
        self.last_run: RunResult | None = None
        self._n = 0

    def _metered(self, url: str) -> str:
        # No provider cost offline; a fake predict_time exercises the
        # "compute / estimate fallback" branch of cost_actual.
        self.last_run = RunResult(urls=[url], predict_time=1.0, metrics={"predict_time": 1.0})
        return url

    def _next(self, ext: str) -> str:
        self._n += 1
        return f"https://fake.local/{self._n}.{ext}"

    def synthesize_voice(
        self, text: str, voice_id: str, model: "str | None" = None
    ) -> str:
        self.voice_calls.append((text, voice_id))
        return self._metered(self._next("mp3"))

    def generate_image(
        self,
        prompt: str,
        size: str,
        aspect_ratio: str,
        image_input: "list[str] | None" = None,
    ) -> str:
        self.image_calls.append((prompt, size, aspect_ratio, image_input))
        return self._metered(self._next("png"))

    def animate_video(
        self,
        prompt: str,
        image_url: str,
        duration: float,
        aspect_ratio: str,
        resolution: str,
        audio_url: str | None = None,
        draft: bool = False,
    ) -> str:
        self.video_calls.append(
            {
                "prompt": prompt,
                "image": image_url,
                "duration": duration,
                "draft": draft,
                "audio": audio_url,
            }
        )
        return self._metered(self._next("mp4"))

    def run_model_metered(self, model_ref: str, params: dict[str, Any]) -> RunResult:
        self.run_calls.append((model_ref, params))
        self.last_run = RunResult(
            urls=[f"https://fake.local/{model_ref}/0.out"],
            predict_time=1.0,
            metrics={"predict_time": 1.0},
        )
        return self.last_run

    def run_model(self, model_ref: str, params: dict[str, Any]) -> list[str]:
        return self.run_model_metered(model_ref, params).urls
