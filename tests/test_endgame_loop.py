"""Endgame — fermeture de la boucle : publication (E3) + perfs réelles → moat (E4).

Prouve offline que **la donnée réelle change la prédiction** : quand les perfs
contredisent l'a priori codé (« POV » sur-performe alors que le défaut classait
« promesse choc » 1er), le prédicteur recalibré **inverse** le classement des hooks.
"""

import pytest

pytest.importorskip("pydantic")

from src.features.performance import FakePerformanceSource, calibrate_angle_weights
from src.features.publish import FakePublisher, PublishError
from src.features.virality import FakeHookGenerator, HookVariant, rank_hooks
from src.studio.api.services.performance import calibrated_predictor
from src.studio.api.services.publish import publish_video

# -- E3 : publication ---------------------------------------------------------

def test_publish_returns_a_deterministic_result():
    res = publish_video("/exports/clip_abc.mp4", platform="tiktok", caption="hello")
    assert res.platform == "tiktok" and res.status == "published"
    assert res.published_id and res.url.startswith("https://tiktok")
    # déterministe : même entrée → même id
    assert publish_video("/exports/clip_abc.mp4").published_id == res.published_id


def test_publish_rejects_empty_video():
    with pytest.raises(PublishError):
        publish_video("   ")


def test_fake_publisher_is_used_by_default():
    assert isinstance(publish_video("x.mp4", publisher=FakePublisher()).published_id, str)


# -- E4 : perfs réelles → recalibration (le moat) -----------------------------

def test_real_performance_inverts_the_ranking():
    """La boucle fermée : perfs réelles → poids appris → le classement suit la RÉALITÉ."""
    angles = ["promesse choc", "POV", "question directe"]
    variants = [HookVariant(id=f"h{i}", angle=a, hook_text="court")
                for i, a in enumerate(angles)]

    # A priori (défauts codés) : « promesse choc » gagne.
    from src.features.virality import FakeViralityPredictor
    a_priori = rank_hooks(variants, FakeViralityPredictor())
    assert a_priori.winner is not None and a_priori.winner.variant.angle == "promesse choc"

    # On « publie » ces angles et on récupère les perfs réelles (POV sur-performe).
    src = FakePerformanceSource()
    signals = [src.fetch(f"pub_{a}", angle=a) for a in angles]
    weights = calibrate_angle_weights(signals)
    assert weights["POV"] > weights["promesse choc"]      # la réalité contredit l'a priori

    # Prédicteur RECALIBRÉ → « POV » gagne désormais.
    learned = calibrated_predictor([(f"pub_{a}", a) for a in angles])
    appris = rank_hooks(variants, learned)
    assert appris.winner is not None and appris.winner.variant.angle == "POV"


def test_end_to_end_generate_then_calibrated_rank():
    """Génère des hooks (Fake) puis les classe avec le prédicteur recalibré."""
    variants = FakeHookGenerator().generate_hooks("un chat dans la neige", n=5)
    published = [(f"pub_{v.angle}", v.angle) for v in variants]
    learned = calibrated_predictor(published)
    ranked = rank_hooks(variants, learned)
    assert ranked.winner is not None
    assert ranked.winner.variant.angle == "POV"            # l'angle qui a marché en vrai
