"""Auto-split déterministe — garantir qu'aucun plan ne dépasse l'horizon du modèle.

« Un plan qui dépasse l'horizon, on le SCINDE en deux — on ne le rabote pas. » Le prompt
MICRO steere déjà le décomposeur vers des plans ≤ horizon (T-DESC-4) ; ceci est le **filet
de sécurité** déterministe pour quand le LLM l'ignore : tout `ShotPlan` VIDÉO plus long que
l'horizon est découpé en sous-plans **de durée égale ≤ horizon**, chaînés par `continuite`,
la narration restant sur le 1er (elle ne se dit qu'une fois). Durée totale préservée.

Ne scinde QUE sur la durée (déterministe, sûr). Pas sur `multi_beat` (heuristique advisory —
cf. `capabilities._beat_count`). La re-décomposition LLM en beats DISTINCTS = enrichissement
futur (E1b) ; ici on garantit d'abord la cohérence temporelle.
"""

from __future__ import annotations

import math

from ...editor.document import Continuite
from .model import ScenePlan, ShotPlan, VideoPlan


def _split_shot(shot: ShotPlan, horizon: float) -> list[ShotPlan]:
    """Découpe un plan vidéo trop long en sous-plans ≤ horizon (sinon renvoie [shot])."""
    if shot.kind != "video" or horizon <= 0 or shot.duree_s <= horizon:
        return [shot]
    n = math.ceil(shot.duree_s / horizon)
    part_s = round(shot.duree_s / n, 2)
    ids = [shot.id] + [f"{shot.id}_p{i + 1}" for i in range(1, n)]
    out: list[ShotPlan] = []
    for i, sid in enumerate(ids):
        prev = shot.continuite.lien_precedent if i == 0 else ids[i - 1]
        nxt = shot.continuite.lien_suivant if i == n - 1 else ids[i + 1]
        out.append(
            shot.model_copy(
                update={
                    "id": sid,
                    "duree_s": part_s,
                    "narration_fr": shot.narration_fr if i == 0 else "",
                    "continuite": Continuite(lien_precedent=prev, lien_suivant=nxt),
                }
            )
        )
    return out


def split_overlong_shots(plan: VideoPlan, *, max_coherent_s: float) -> VideoPlan:
    """Renvoie une copie du plan où aucun `ShotPlan` vidéo ne dépasse l'horizon."""
    scenes: list[ScenePlan] = []
    for scene in plan.scenes:
        shots: list[ShotPlan] = []
        for shot in scene.shots:
            shots.extend(_split_shot(shot, max_coherent_s))
        scenes.append(scene.model_copy(update={"shots": shots}))
    return plan.model_copy(update={"scenes": scenes})
