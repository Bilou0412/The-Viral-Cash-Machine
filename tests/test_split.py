"""E1 — auto-split : aucun plan vidéo ne dépasse l'horizon (on scinde, on ne rabote pas)."""

import pytest

pytest.importorskip("pydantic")

from src.features.scenes.model import ScenePlan, ShotPlan, VideoPlan
from src.features.scenes.split import split_overlong_shots


def _plan(shot: ShotPlan) -> VideoPlan:
    return VideoPlan(scenes=[ScenePlan(id="s1", shots=[shot])])


def test_overlong_shot_is_split_not_clamped():
    plan = _plan(ShotPlan(id="sh1", kind="video", duree_s=8.0, narration_fr="salut"))
    out = split_overlong_shots(plan, max_coherent_s=5.0)
    shots = out.scenes[0].shots
    assert len(shots) == 2                                   # 8 s → 2 sous-plans
    assert [s.id for s in shots] == ["sh1", "sh1_p2"]
    assert all(s.duree_s <= 5.0 for s in shots)             # chacun ≤ horizon
    assert round(sum(s.duree_s for s in shots), 1) == 8.0   # durée totale préservée
    assert shots[0].narration_fr == "salut" and shots[1].narration_fr == ""  # 1er porte la voix
    assert shots[0].continuite.lien_suivant == "sh1_p2"     # chaînés
    assert shots[1].continuite.lien_precedent == "sh1"


def test_shot_within_horizon_is_untouched():
    plan = _plan(ShotPlan(id="sh1", kind="video", duree_s=4.0))
    out = split_overlong_shots(plan, max_coherent_s=5.0)
    assert [s.id for s in out.scenes[0].shots] == ["sh1"]


def test_photo_shot_is_never_split():
    plan = _plan(ShotPlan(id="env", kind="photo", duree_s=9.0))  # photo = pas d'i2v
    out = split_overlong_shots(plan, max_coherent_s=5.0)
    assert [s.id for s in out.scenes[0].shots] == ["env"]


def test_generate_video_plan_never_exceeds_horizon():
    """Bout-en-bout offline : le service applique le filet (aucun plan > horizon)."""
    from src.features.scenes.model import ShotCharacterPlan
    from src.features.scenes.ports import SceneVideoDecomposer

    class _Overlong:  # décomposeur de test qui produit un plan trop long
        def decompose_video(self, prompt, **kw) -> VideoPlan:
            return _plan(ShotPlan(id="sh1", kind="video", duree_s=12.0,
                                  personnages=[ShotCharacterPlan(name="Léa")]))

        def plan_arc(self, prompt, **kw):
            return []

    from src.studio.api.services.scenes import generate_video_plan

    dec: SceneVideoDecomposer = _Overlong()  # type: ignore[assignment]
    plan = generate_video_plan("idée", decomposer=dec)
    durations = [sh.duree_s for sc in plan.scenes for sh in sc.shots]
    assert durations and all(d <= 5.0 for d in durations)   # p-video horizon = 5 s
