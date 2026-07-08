"""Editable price table — single source for estimate rates + real-cost rates.

Loaded once from ``prices.json`` (next to this module) or from the path in
``VCM_PRICES_PATH``. Lets the owner tune prices without a code deploy. Pure
read; no DB. ``pricing.py`` (estimate) and ``cost_actual.py`` (real) both read here.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "prices.json")


@lru_cache(maxsize=1)
def _table() -> dict[str, Any]:
    path = os.environ.get("VCM_PRICES_PATH", _DEFAULT_PATH)
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data


# -- estimate rates (pre-flight) --------------------------------------------

def _estimate() -> dict[str, Any]:
    est: dict[str, Any] = _table().get("estimate", {})
    return est


def estimate_image_usd() -> float:
    return float(_estimate().get("image_usd", 0.03))


def estimate_video_usd_per_s() -> float:
    return float(_estimate().get("video_usd_per_s", 0.05))


def estimate_voice_usd_per_kchar() -> float:
    return float(_estimate().get("voice_usd_per_kchar", 0.02))


def draft_video_multiplier() -> float:
    return float(_estimate().get("draft_video_multiplier", 0.4))


def beat_video_seconds() -> float:
    return float(_estimate().get("beat_video_seconds", 7.0))


# -- real-cost rates (post-flight) ------------------------------------------

def compute_usd_per_s(model_ref: str) -> float:
    """Replicate hardware $/s for a model (0 = unknown → caller uses estimate)."""
    rates = _table().get("compute_usd_per_s", {})
    return float(rates.get(model_ref, rates.get("default", 0.0)))
