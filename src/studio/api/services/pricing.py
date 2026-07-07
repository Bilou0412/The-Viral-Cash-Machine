"""Cost model for studio generation — pure, no I/O, no DB.

The Replicate models bill per second (video), per image, or per character of
synthesized speech. We keep the rate card in one place so `estimate_cost`
(pre-flight, before any generation) and the per-job `CostEntry` accounting
(post-flight, recorded by the API) agree on the same numbers.

Rates are approximate published Replicate prices and intentionally easy to tune;
they are NOT a contract with the provider, only a planning aid for the cost HUD.
"""

from dataclasses import dataclass

from ....features.assets.models import IMAGE_MODEL, VIDEO_MODEL, VOICE_MODEL
from . import price_table

# Slugs Replicate — source unique de vérité dans features/assets/models.py.
MODEL_IMAGE = IMAGE_MODEL
MODEL_VIDEO = VIDEO_MODEL
MODEL_VOICE = VOICE_MODEL

# Default motion duration per video beat (seconds). Mirrors Pipeline.generate_assets.
BEAT_VIDEO_SECONDS = price_table.beat_video_seconds()

# Estimate rates now live in prices.json (editable). These module names are kept
# for back-compat but resolve to the table; the real post-flight cost is in
# cost_actual.py.
RATE_IMAGE_USD = price_table.estimate_image_usd()
RATE_VIDEO_USD_PER_S = price_table.estimate_video_usd_per_s()
RATE_VOICE_USD_PER_KCHAR = price_table.estimate_voice_usd_per_kchar()
DRAFT_VIDEO_MULTIPLIER = price_table.draft_video_multiplier()


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
