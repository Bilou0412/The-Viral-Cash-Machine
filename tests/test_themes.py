"""Tests du thème (DA en donnée) + cascade de résolution (LOT 1.4).

Contrats :
1. Le thème « horror » reproduit VERBATIM les constantes de prompts.py (garde golden).
2. La cascade `resolve` respecte la précédence asset ▸ bloc ▸ thème.
3. Passer un autre `Theme` change réellement la DA dans les prompts produits ;
   `theme=None` (défaut) reste identique au comportement horror.
"""

import pytest

pytest.importorskip("pydantic")

from src.features.scripting import prompts as P
from src.features.scripting.themes import (
    HORROR,
    Theme,
    get_theme,
    register_theme,
    resolve,
)


def _toy_theme() -> Theme:
    """Un thème de test, fragments tous distincts de horror."""
    return Theme(
        name="toytheme",
        da="bright pastel daydream, soft diffuse light",
        pov="Third-person wide shot",
        pov_hands="no hands visible",
        no_text="NO_TEXT_TOY",
        voice_only_audio="VOICE_TOY",
        ambient_audio="AMBIENT_TOY",
        vertical="Square 1:1.",
        pace_calm="PACE_CALM_TOY",
        pace_sudden="PACE_SUDDEN_TOY",
        decomposer_tone="whimsical pastel",
    )


def test_horror_theme_matches_prompts_constants():
    """Le défaut « horror » == les constantes de module (rien n'a bougé)."""
    h = get_theme("horror")
    assert h is HORROR
    assert h.da == P.DA
    assert h.pov == P.POV
    assert h.pov_hands == P.POV_HANDS
    assert h.no_text == P.NO_TEXT
    assert h.vertical == P.VERTICAL
    assert h.pace_calm == P.PACE_CALM
    assert h.pace_sudden == P.PACE_SUDDEN
    assert h.ambient_audio == P.AMBIENT_AUDIO
    assert h.voice_only_audio == P.VOICE_ONLY_AUDIO


def test_get_theme_unknown_raises():
    with pytest.raises(KeyError):
        get_theme("does-not-exist")


def test_resolve_cascade_precedence():
    # asset bat tout
    assert resolve("A", "B", "T") == "A"
    # sinon bloc
    assert resolve(None, "B", "T") == "B"
    # sinon thème
    assert resolve(None, None, "T") == "T"


def test_default_theme_is_byte_identical_to_horror():
    """frame avec theme=None == frame avec theme=horror == ancien comportement."""
    none_frame = P.frame_action("Léo", "a tall man", "a dark cave")
    horror_frame = P.frame_action("Léo", "a tall man", "a dark cave", get_theme("horror"))
    assert none_frame == horror_frame
    assert P.DA in none_frame


def test_other_theme_changes_da_in_prompt():
    """Un autre thème injecte SA DA et retire celle de horror."""
    toy = _toy_theme()
    frame = P.frame_action("Léo", "a tall man", "a sunny meadow", toy)
    assert toy.da in frame
    assert P.DA not in frame          # plus la DA horror
    assert toy.no_text in frame
    assert toy.vertical in frame
    # le motion suit aussi le thème
    motion = P.motion_action("Léo", "walks ahead", toy)
    assert toy.pace_calm in motion
    assert toy.ambient_audio in motion


def test_theme_flows_through_round_prompts():
    """Le thème passé à script_prompts/round_prompts atteint les prompts."""
    from src.features.scripting import adventure_to_prompts as A2P
    from src.features.scripting.fake_adventure_decomposer import (
        FakeAdventureDecomposer,
    )

    toy = _toy_theme()
    s = FakeAdventureDecomposer().decompose_adventure("cave", "Léo", "Sam")
    rps = A2P.script_prompts(s, "left", toy)
    for rp in rps:
        for beat in rp.video_beats():
            assert P.DA not in beat.frame
        for img in rp.choice_images:
            assert toy.da in img
    epi = A2P.epilogue_beat(s, "left", toy)
    assert toy.da in epi.frame


def test_register_theme_roundtrip():
    toy = _toy_theme()
    register_theme(toy)
    assert get_theme("toytheme") is toy


def test_list_themes_shape_and_horror_label():
    """L'API /themes : liste de {name, label} ; horror libellé 'Horreur'."""
    from src.features.scripting.themes import list_themes

    items = list_themes()
    assert all(set(it) == {"name", "label"} for it in items)
    horror = next(it for it in items if it["name"] == "horror")
    assert horror["label"] == "Horreur"
