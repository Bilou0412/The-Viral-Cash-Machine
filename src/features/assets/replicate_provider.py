"""Replicate-based asset generation."""

from typing import Any, Dict, List, Optional
from .ports import AssetProvider, RunResult


def _normalize_outputs(result: Any) -> List[str]:
    """Normalize a replicate.run(...) result into a list of URL strings.

    Handles the shapes replicate returns across models:
    - a single str / URL                       -> ["<url>"]
    - a FileOutput-like object (has .url)       -> ["<obj.url>"]
    - any other single object                   -> [str(obj)]
    - a list of any of the above                -> [<each normalized>...]
    - a dict with a url-ish field               -> ["<url>"]
    """
    # A list/tuple of outputs: normalize each element (flatten one level).
    if isinstance(result, (list, tuple)):
        out: List[str] = []
        for item in result:
            out.extend(_normalize_outputs(item))
        return out

    # A dict output: pull a url-ish field if present, else str() the dict.
    if isinstance(result, dict):
        for key in ("url", "output", "audio", "video", "image"):
            if key in result and result[key] is not None:
                return _normalize_outputs(result[key])
        return [str(result)]

    # A FileOutput-like object exposing a `.url` attribute.
    url = getattr(result, "url", None)
    if isinstance(url, str) and url:
        return [url]

    # Plain str / URL, or any other object: stringify.
    return [str(result)]


class ReplicateAssetProvider(AssetProvider):
    """Generate assets using Replicate AI models.

    ``api_token`` (B.2) : le token Replicate de l'utilisateur courant. Passé au
    client SDK à chaque appel (plus de lecture implicite de ``REPLICATE_API_TOKEN``
    dans l'environnement, qui serait partagée entre utilisateurs).
    """

    def __init__(self, api_token: Optional[str] = None) -> None:
        self.api_token = api_token
        self.last_run: Optional[RunResult] = None

    def _client(self) -> Any:
        from replicate.client import Client

        return Client(api_token=self.api_token) if self.api_token else Client()

    def run_model_metered(
        self, model_ref: str, params: Dict[str, Any]
    ) -> RunResult:
        """Run a model via the predictions API to capture real cost/metrics.

        Defensive: if the predictions path fails for any SDK-shape reason, fall
        back to ``client.run`` (outputs only, no metrics) so generation never
        breaks — the cost layer then falls back to the estimate.
        """
        client = self._client()
        result: RunResult
        try:
            pred = client.models.predictions.create(model_ref, input=params)
            pred.wait()
            metrics: Dict[str, Any] = dict(pred.metrics or {})
            predict_time = metrics.get("predict_time")
            cost = getattr(pred, "cost", None)
            result = RunResult(
                urls=_normalize_outputs(pred.output),
                cost_usd=float(cost) if cost is not None else None,
                predict_time=(
                    float(predict_time) if predict_time is not None else None
                ),
                metrics=metrics,
            )
        except Exception:
            result = RunResult(urls=_normalize_outputs(client.run(model_ref, input=params)))
        self.last_run = result
        return result

    def run_model(self, model_ref: str, params: Dict[str, Any]) -> List[str]:
        """Run an arbitrary Replicate model and normalize its output URL(s)."""
        return self.run_model_metered(model_ref, params).urls

    def synthesize_voice(
        self, text: str, voice_id: str, model: Optional[str] = None
    ) -> str:
        """Synthesize voice using a Minimax Speech model.

        `model` lets a cloned voice use the model it was cloned with
        (e.g. "minimax/speech-02-hd"). Default = "minimax/speech-2.8-turbo".
        """
        input: Dict[str, Any] = {
            "text": text,
            "voice_id": voice_id,
        }
        return self.run_model(model or "minimax/speech-2.8-turbo", input)[0]

    def generate_image(
        self,
        prompt: str,
        size: str,
        aspect_ratio: str,
        image_input: Optional[list[str]] = None,
    ) -> str:
        """Generate image using ByteDance SeedDream model.

        `image_input` : 1-14 images de référence (image-to-image) — garde le
        personnage et la DA cohérents (validé : seedream-4.5 `image_input`).
        """
        input: Dict[str, Any] = {
            "prompt": prompt,
            "size": size,
            "aspect_ratio": aspect_ratio,
        }
        if image_input:
            input["image_input"] = image_input
        return self.run_model("bytedance/seedream-4.5", input)[0]

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
        input: Dict[str, Any] = {
            "prompt": prompt,
            "image": image_url,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "draft": draft,
            "save_audio": True,
        }
        if audio_url:
            input["audio"] = audio_url
        return self.run_model("prunaai/p-video", input)[0]
