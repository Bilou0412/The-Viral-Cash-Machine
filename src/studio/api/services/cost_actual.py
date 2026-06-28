"""Compute the REAL post-flight cost of a generation from its RunResult.

Priority:
  1. provider's billed ``cost_usd`` if present (source="provider"),
  2. else ``predict_time × hardware_rate`` from the price table (source="compute"),
  3. else fall back to the pre-flight rate-card estimate (source="estimate").

So OpenAI/Whisper (exact) and any Replicate model that returns a cost or has a
configured hardware rate get a REAL number; everything else degrades to the
estimate, tagged transparently.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ....features.assets.ports import RunResult
from . import price_table
from .pricing import CostLine


@dataclass(frozen=True)
class ActualCost:
    line: CostLine            # model/units/unit_kind from the estimate; amount = real
    source: str              # "provider" | "compute" | "estimate"
    predict_time_s: Optional[float] = None


def actual_cost(
    model_ref: str, estimate_line: CostLine, run: Optional[RunResult]
) -> ActualCost:
    """Resolve the real cost for one generated node."""
    predict_time = run.predict_time if run is not None else None

    if run is not None and run.cost_usd is not None and run.cost_usd > 0:
        line = replace(estimate_line, amount_usd=round(run.cost_usd, 6))
        return ActualCost(line, "provider", predict_time)

    rate = price_table.compute_usd_per_s(model_ref)
    if predict_time and rate > 0:
        line = replace(estimate_line, amount_usd=round(predict_time * rate, 6))
        return ActualCost(line, "compute", predict_time)

    return ActualCost(estimate_line, "estimate", predict_time)
