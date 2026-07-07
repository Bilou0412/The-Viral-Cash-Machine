"""Source de perfs FAKE — déterministe, hors-ligne (dev + tests).

Synthétise des perfs stables à partir de l'angle (une empreinte différente du proxy
LLM-juge : ici « POV » sur-performe, à l'inverse du défaut codé — pour PROUVER que la
calibration inverse bien le classement quand la donnée réelle contredit l'a priori)."""

from __future__ import annotations

from .model import PerformanceSignal

# Rétention réelle (simulée) par angle — délibérément DIFFÉRENTE des poids a priori.
_REAL_RETENTION: dict[str, float] = {
    "POV": 0.92,               # sur-performe dans la vraie vie (à rebours du défaut)
    "question directe": 0.80,
    "compte à rebours": 0.66,
    "in medias res": 0.55,
    "promesse choc": 0.40,     # sous-performe (le défaut le classait 1er)
}


class FakePerformanceSource:
    """Implémente `PerformanceSource` sans réseau (perfs déterministes par angle)."""

    def fetch(self, published_id: str, *, angle: str = "") -> PerformanceSignal:
        ret = _REAL_RETENTION.get(angle, 0.5)
        return PerformanceSignal(
            published_id=published_id, angle=angle,
            views=int(10_000 * ret), completion_rate=round(ret * 0.7, 3),
            hook_retention_2s=ret,
        )
