"""Calibration — perfs réelles agrégées → poids d'angle APPRIS (le cœur du moat).

Pur, déterministe. Moyenne la rétention à 2 s par angle et la projette en poids 0..100,
directement consommables par `FakeViralityPredictor(angle_weights=...)`. Le prédicteur
cesse de deviner (a priori codé) et se cale sur ce qui a VRAIMENT retenu l'attention."""

from __future__ import annotations

from collections import defaultdict

from .model import PerformanceSignal


def calibrate_angle_weights(signals: list[PerformanceSignal]) -> dict[str, float]:
    """`{angle: poids 0..100}` = moyenne de `hook_retention_2s` par angle (× 100)."""
    by_angle: dict[str, list[float]] = defaultdict(list)
    for s in signals:
        if s.angle.strip():
            by_angle[s.angle].append(s.hook_retention_2s)
    return {
        angle: round(sum(vals) / len(vals) * 100.0, 1)
        for angle, vals in by_angle.items()
    }
