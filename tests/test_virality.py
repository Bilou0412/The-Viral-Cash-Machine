"""Boucle VIRALITÉ — N variantes de hook → prédiction → classement (offline, Fake)."""

import pytest

pytest.importorskip("pydantic")

from src.features.virality import (
    FakeHookGenerator,
    FakeViralityPredictor,
    HookVariant,
    rank_hooks,
)
from src.studio.api.services.virality import propose_hooks


def test_fake_generator_yields_distinct_angles():
    hooks = FakeHookGenerator().generate_hooks("un chat qui joue dans la neige", n=3)
    assert len(hooks) == 3
    assert len({h.angle for h in hooks}) == 3          # 3 angles distincts
    assert all(h.hook_text and h.first_shot_prompt for h in hooks)


def test_rank_sorts_by_predicted_virality_desc():
    variants = [
        HookVariant(id="a", angle="POV", hook_text="court"),               # base 66
        HookVariant(id="b", angle="promesse choc", hook_text="court"),     # base 82 → gagne
        HookVariant(id="c", angle="question directe", hook_text="court"),  # base 70
    ]
    ranked = rank_hooks(variants, FakeViralityPredictor())
    overalls = [s.score.overall for s in ranked.variants]
    assert overalls == sorted(overalls, reverse=True)   # trié décroissant
    assert ranked.winner is not None
    assert ranked.winner.variant.angle == "promesse choc"   # l'angle le plus fort gagne


def test_propose_hooks_offline_returns_ranked_winner():
    ranked = propose_hooks("une recette de carbonara", n_variants=3, openai_key=None)
    assert len(ranked.variants) == 3
    assert ranked.winner is ranked.variants[0]           # gagnante = tête de classement
    # la gagnante a la meilleure note globale
    assert all(ranked.winner.score.overall >= s.score.overall for s in ranked.variants)
