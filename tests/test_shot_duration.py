"""T-DESC-4 — discipline de durée : horizon = capacité modèle, split-pas-clamp, fallback-qui-crie.

Couvre : la table de capacités (horizon 5 s p-video), `validate_shot_duration` (les 5 cas :
over_horizon / missing / multi_beat / geste-phrasé-OK / shot=None), le garde-fou API du
décomposeur (une durée > horizon N'EST PAS rabotée en silence), et — le test qui compte — le
**chemin coût atteint SANS préflight** doit CRIER sur une durée manquante.
"""

import logging

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_shot_duration
from src.editor.document import (
    ClipBrick,
    GenNode,
    Segment,
    ShotBrief,
    TimelinePlacement,
)
from src.features.assets.models import (
    VIDEO_MODEL,
    effective_video_slug,
    max_coherent_duration_s,
)

# -- source unique : horizon = capacité du modèle -----------------------------

def test_horizon_is_a_model_capability():
    assert max_coherent_duration_s("prunaai/p-video") == 5.0
    assert max_coherent_duration_s(VIDEO_MODEL) == 5.0
    # slug inconnu → défaut prudent (jamais 0 / None).
    assert max_coherent_duration_s("acme/unknown-model") == 5.0
    # UN seul point de résolution : version ignorée, vide → modèle par défaut.
    assert effective_video_slug("prunaai/p-video:abc123") == "prunaai/p-video"
    assert effective_video_slug("") == VIDEO_MODEL


def _video_clip(*, duration=None, placement_s=4.0, timeline=None, shot=True, bid="v1"):
    motion_params = {"image": "x", "prompt": "p"}
    if duration is not None:
        motion_params["duration"] = duration
    return ClipBrick(
        id=bid, kind="video",
        image=GenNode(model_ref="img", params={"prompt": "p"}),
        motion=GenNode(model_ref=VIDEO_MODEL, params=motion_params),
        shot=ShotBrief(timeline=timeline or []) if shot else None,
        placement=TimelinePlacement(track=0, start=0.0, duration=placement_s),
    )


# -- validate_shot_duration : les 5 cas ---------------------------------------

def test_over_horizon_is_flagged_not_clamped():
    """Un plan de 7 s (horizon 5) est REJETÉ (signal de split), pas raboté."""
    out = validate_shot_duration(_video_clip(duration=7.0), max_coherent_s=5.0)
    assert out == {"motion": ["over_horizon"]}


def test_missing_duration_is_flagged():
    """Durée absente (ni motion ni placement) = donnée corrompue → 'missing'."""
    out = validate_shot_duration(_video_clip(duration=None, placement_s=0.0), max_coherent_s=5.0)
    assert out == {"motion": ["missing"]}


def test_multi_beat_flagged_on_distinct_actions():
    """Deux actions distinctes dans la timeline → à scinder."""
    tl = [Segment(action_sujet="she walks in"), Segment(action_sujet="she sits down")]
    out = validate_shot_duration(_video_clip(duration=4.0, timeline=tl), max_coherent_s=5.0)
    assert out == {"beats": ["multi_beat"]}


def test_single_gesture_phrasing_is_ok():
    """Plusieurs segments qui PHRASENT le même geste (même action_sujet) = 1 beat → OK."""
    tl = [Segment(action_sujet="raises the cup"), Segment(action_sujet="raises the cup"),
          Segment(action_sujet="raises the cup")]
    out = validate_shot_duration(_video_clip(duration=4.0, timeline=tl), max_coherent_s=5.0)
    assert out == {}


def test_shot_none_is_never_judged():
    assert validate_shot_duration(_video_clip(duration=99.0, shot=False), max_coherent_s=5.0) == {}


def test_audit_flags_only_problem_clips():
    """La diagnose de doc ne retient que les briques à problème (par id)."""
    from src.editor.capabilities import audit_shot_durations
    from src.editor.document import EditorDocument

    doc = EditorDocument(bricks=[
        _video_clip(duration=4.0, bid="ok"),        # dans l'horizon
        _video_clip(duration=8.0, bid="toolong"),   # > horizon 5
    ])
    audit = audit_shot_durations(doc, max_coherent_s=5.0)
    assert set(audit) == {"toolong"}
    assert audit["toolong"] == {"motion": ["over_horizon"]}


# -- décomposeur : borne API, PAS clamp d'horizon -----------------------------

def test_decomposer_does_not_silently_squash_over_horizon():
    from src.features.scenes.openai_scene_decomposer import _PARAM_MAX_S, _sane_duration

    assert _sane_duration(7.0) == 7.0        # > horizon 5 mais PASSE (sera flaggé, pas raboté)
    assert _sane_duration(40.0) == _PARAM_MAX_S   # absurde → borné au max du champ API
    assert _sane_duration(-3.0) == 1.0       # absurde → plancher API


# -- co-défense : le chemin COÛT (sans préflight) doit CRIER -------------------

def test_cost_path_without_preflight_screams_on_missing_duration(caplog):
    """Une durée trouée qui entre DIRECTEMENT par le coût (retry/régé/import, sans
    repasser par le préflight) ne doit jamais être facturée en silence."""
    from src.studio.api.services.editor_generation import _best_effort_cost

    with caplog.at_level(logging.WARNING, logger="src.studio.api.services.editor_generation"):
        line = _best_effort_cost(VIDEO_MODEL, "video", {}, draft=False)  # params sans 'duration'
    assert any("durée manquante" in r.message for r in caplog.records)
    assert line.amount_usd > 0  # le coût est quand même émis (best-effort, ne bloque jamais)
