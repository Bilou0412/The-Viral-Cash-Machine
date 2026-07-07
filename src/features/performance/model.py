"""Modèles de PERFORMANCE — le signal réel qui ferme la boucle (le moat).

Une vidéo publiée renvoie des perfs (rétention, complétion). Agrégées par ANGLE de hook,
elles **recalibrent** le prédicteur de viralité : la structure n'est plus devinée, elle est
APPRISE. C'est ce que LTX Studio ne peut pas copier en donnant une toile blanche."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PerformanceSignal(_M):
    """Les perfs réelles d'UNE vidéo publiée, portant l'angle du hook qui l'a ouverte."""

    published_id: str
    angle: str = ""                # l'angle du hook publié (la clé de calibration)
    views: int = 0
    completion_rate: float = 0.0   # 0..1 — % qui vont au bout
    hook_retention_2s: float = 0.0  # 0..1 — rétention à 2 s (le signal le plus prédictif)
