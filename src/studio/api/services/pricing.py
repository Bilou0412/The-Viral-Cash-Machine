"""Cost model for studio generation — pure, no I/O, no DB.

The Replicate models bill per second (video), per image, or per character of
synthesized speech. We keep the rate card in one place so `estimate_cost`
(pre-flight, before any generation) and the per-job `CostEntry` accounting
(post-flight, recorded by the API) agree on the same numbers.

Rates are approximate published Replicate prices and intentionally easy to tune;
they are NOT a contract with the provider, only a planning aid for the cost HUD.
"""

from dataclasses import dataclass

# Replicate model identifiers (kept in sync with features/assets/replicate_provider).
MODEL_IMAGE = "bytedance/seedream-4.5"
MODEL_VIDEO = "prunaai/p-video"
MODEL_VOICE = "minimax/speech-2.8-turbo"

# Default motion duration per video beat (seconds). Mirrors Pipeline.generate_assets.
BEAT_VIDEO_SECONDS = 7.0

# Rate card (USD). unit_kind is recorded on each CostEntry alongside the amount.
RATE_IMAGE_USD = 0.03          # per generated image
RATE_VIDEO_USD_PER_S = 0.05    # per second of generated video
RATE_VOICE_USD_PER_KCHAR = 0.02  # per 1000 characters of synthesized speech

# A draft pass is cheaper (lower resolution / fewer steps); applied to video only.
DRAFT_VIDEO_MULTIPLIER = 0.4


@dataclass(frozen=True)
class CostLine:
    """One line of the estimate: a model, how many units, and the amount."""

    model: str
    units: float
    unit_kind: str   # "image" | "second" | "kchar"
    amount_usd: float


@dataclass(frozen=True)
class CostEstimate:
    """Full pre-flight estimate for an episode's asset generation."""

    lines: tuple[CostLine, ...]

    @property
    def total_usd(self) -> float:
        return round(sum(line.amount_usd for line in self.lines), 4)


def image_cost(n_images: int) -> CostLine:
    amount = round(n_images * RATE_IMAGE_USD, 4)
    return CostLine(MODEL_IMAGE, float(n_images), "image", amount)


def video_cost(seconds: float, draft: bool = False) -> CostLine:
    mult = DRAFT_VIDEO_MULTIPLIER if draft else 1.0
    amount = round(seconds * RATE_VIDEO_USD_PER_S * mult, 4)
    return CostLine(MODEL_VIDEO, round(seconds, 2), "second", amount)


def voice_cost(n_chars: int) -> CostLine:
    kchar = n_chars / 1000.0
    amount = round(kchar * RATE_VOICE_USD_PER_KCHAR, 4)
    return CostLine(MODEL_VOICE, round(kchar, 4), "kchar", amount)
