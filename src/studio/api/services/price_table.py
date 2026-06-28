"""Editable price table — single source for estimate rates + real-cost rates.

Loaded once from ``prices.json`` (next to this module) or from the path in
``VCM_PRICES_PATH``. Lets the owner tune prices without a code deploy. Pure
read; no DB. ``pricing.py`` (estimate) and ``cost_actual.py`` (real) both read here.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "prices.json")


@lru_cache(maxsize=1)
def _table() -> Dict[str, Any]:
    path = os.environ.get("VCM_PRICES_PATH", _DEFAULT_PATH)
    with open(path, encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return data


def reload_prices() -> None:
    """Drop the cache (e.g. after editing prices.json at runtime)."""
    _table.cache_clear()


# -- estimate rates (pre-flight) --------------------------------------------

def _estimate() -> Dict[str, Any]:
    est: Dict[str, Any] = _table().get("estimate", {})
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


def openai_per_mtoken(model: str) -> tuple[float, float]:
    """(input, output) USD per 1M tokens for an OpenAI model."""
    table = _table().get("openai_per_mtoken", {})
    rule = table.get(model, table.get("default", {"in": 0.15, "out": 0.60}))
    return float(rule.get("in", 0.0)), float(rule.get("out", 0.0))


def whisper_usd_per_minute() -> float:
    return float(_table().get("whisper_usd_per_minute", 0.006))
