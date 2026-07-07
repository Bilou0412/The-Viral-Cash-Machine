"""Feature PERFORMANCE — la boucle fermée (perfs réelles → prédicteur recalibré = le moat)."""

from .calibrate import calibrate_angle_weights
from .fake_source import FakePerformanceSource
from .model import PerformanceSignal
from .ports import PerformanceError, PerformanceSource

__all__ = [
    "FakePerformanceSource",
    "PerformanceError",
    "PerformanceSignal",
    "PerformanceSource",
    "calibrate_angle_weights",
]
