"""Tests du compilateur de contexte récit (E6)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.context import compile_prompt, merge_context  # noqa: E402
from src.editor.document import NarrativeContext  # noqa: E402


def test_global_inherited_when_no_override():
    g = NarrativeContext(text="dans la mine", art_direction="dark horror")
    assert merge_context(g, None) is g
    p = compile_prompt("a cave", g)
    assert "a cave" in p
    assert "dark horror" in p
    assert "Story context: dans la mine" in p


def test_local_override_wins():
    g = NarrativeContext(text="trame globale", art_direction="horror")
    o = NarrativeContext(art_direction="bright pastel")  # surcharge la DA
    merged = merge_context(g, o)
    assert merged.art_direction == "bright pastel"   # local gagne
    assert merged.text == "trame globale"            # hérité (override vide)
    p = compile_prompt("a meadow", g, o)
    assert "bright pastel" in p
    assert "horror" not in p


def test_characters_merged():
    g = NarrativeContext(characters={"Léo": "tall man"})
    o = NarrativeContext(characters={"Sam": "short woman"})
    merged = merge_context(g, o)
    assert merged.characters == {"Léo": "tall man", "Sam": "short woman"}
    p = compile_prompt("scene", g, o)
    assert "Léo: tall man" in p and "Sam: short woman" in p


def test_theme_da_flows_into_prompt():
    from src.features.scripting.themes import get_theme

    g = NarrativeContext(art_direction=get_theme("horror").da)
    p = compile_prompt("a tunnel", g)
    assert get_theme("horror").da in p


def test_template_prefix_leads():
    g = NarrativeContext()
    p = compile_prompt("subject", g, template_prefix="wide cinematic shot")
    assert p.startswith("wide cinematic shot")


def test_include_story_toggle_for_voice():
    g = NarrativeContext(text="longue trame")
    # une voix : le texte parlé est déjà le base_prompt, on n'inonde pas de trame
    p = compile_prompt("tu avances dans le noir", g, include_story=False)
    assert "longue trame" not in p
    assert "tu avances dans le noir" in p


def test_empty_yields_empty():
    assert compile_prompt("", NarrativeContext()) == ""
