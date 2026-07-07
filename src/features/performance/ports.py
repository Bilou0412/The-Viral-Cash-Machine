"""Port de PERFORMANCE (`typing.Protocol`) — récupérer les perfs d'une vidéo publiée.

Impl Fake (offline/tests) ; l'impl réelle (analytics plateforme) est un swap au bord."""

from __future__ import annotations

from typing import Protocol

from .model import PerformanceSignal


class PerformanceError(RuntimeError):
    """Perfs indisponibles (analytics injoignable, id inconnu…)."""


class PerformanceSource(Protocol):
    def fetch(self, published_id: str, *, angle: str = "") -> PerformanceSignal: ...
