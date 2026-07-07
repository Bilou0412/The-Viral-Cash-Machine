"""Performance service — fermer la boucle : perfs réelles → prédicteur recalibré (moat).

Fake par défaut (offline) ; l'impl réelle (analytics plateforme) est un swap au bord.
Le prédicteur recalibré s'injecte dans `propose_hooks(predictor=...)` → le classement des
hooks suit désormais ce qui a VRAIMENT marché, pas l'a priori codé."""

from __future__ import annotations

from ....features.performance import (
    FakePerformanceSource,
    PerformanceSource,
    calibrate_angle_weights,
)
from ....features.virality import FakeViralityPredictor, ViralityPredictor


def get_performance_source() -> PerformanceSource:
    """La source de perfs active (Fake tant que l'analytics plateforme n'est pas câblée)."""
    return FakePerformanceSource()


def calibrated_predictor(
    published: list[tuple[str, str]],
    *,
    source: PerformanceSource | None = None,
) -> ViralityPredictor:
    """`(published_id, angle)[]` → prédicteur de viralité **recalibré** sur les perfs réelles.

    À injecter dans `propose_hooks(predictor=...)`. Sans historique → défauts a priori."""
    src = source or get_performance_source()
    signals = [src.fetch(pid, angle=angle) for pid, angle in published]
    weights = calibrate_angle_weights(signals)
    return FakeViralityPredictor(angle_weights=weights or None)
