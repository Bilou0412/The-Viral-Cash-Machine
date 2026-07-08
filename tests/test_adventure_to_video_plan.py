"""Tests de l'adaptateur `adventure_to_video_plan` : AdventureScript → VideoPlan (rail v5).

Le CYOA horreur passe désormais par le rail UNIQUE (`.claude/rules/architecture.md`) :
`AdventureScript → VideoPlan → EditorDocument`. Il hérite donc de `compile_shot`
(prompts courts), `describe_document` (texte) et `document_to_spec`. On verrouille ici
les invariants de STRUCTURE (manches→scènes, 2 persos en bible, plans valides, sujet
libre porté jusqu'au prompt, DA/POV du thème dans le style) — offline, Fake.
"""

import pytest

pytest.importorskip("pydantic")

from src.editor import document_to_spec
from src.editor.capabilities import validate_clip
from src.editor.describe import describe_document
from src.editor.document import ClipBrick
from src.features.scenes.scene_plan_to_document import scene_plan_to_document
from src.features.scripting.adventure_to_video_plan import adventure_to_video_plan
from src.features.scripting.fake_adventure_decomposer import FakeAdventureDecomposer
from src.features.scripting.themes import Theme


def _script(n_rounds: int):
    return FakeAdventureDecomposer().decompose_adventure(
        "cave", "Léo", "Sam", n_rounds=n_rounds
    )


def _doc(n_rounds: int):
    return scene_plan_to_document(adventure_to_video_plan(_script(n_rounds)))


@pytest.mark.parametrize("n", [1, 3])
def test_structure_intro_rounds_epilogue(n):
    """N manches → intro + N scènes de manche + épilogue = N+2 scènes."""
    doc = _doc(n)
    assert len(doc.scenes) == n + 2
    assert doc.scenes[0].id == "intro"
    assert doc.scenes[-1].id == "epilogue"
    assert [s.id for s in doc.scenes[1:-1]] == [f"round{i}" for i in range(1, n + 1)]


def test_two_characters_in_bible():
    doc = _doc(2)
    names = {c.name for c in doc.bible}
    assert names == {"Léo", "Sam"}


def test_all_plans_valid_and_compilable():
    """Chaque plan v5 est complet (validate_clip vide) et le spec se construit."""
    doc = _doc(2)
    shots = [b for b in doc.bricks if isinstance(b, ClipBrick) and b.shot is not None]
    assert shots, "le CYOA doit produire des briques .shot (pas des blobs)"
    for b in shots:
        assert validate_clip(b) == {}, b.id
    spec = document_to_spec(doc)  # refs valides, ne lève pas
    assert spec.segments


def test_describe_is_not_empty():
    """Le CYOA est VISIBLE en texte (le descripteur ne rend plus un doc vide)."""
    txt = describe_document(_doc(2))
    assert "SCÈNE round1" in txt
    assert "PERSONNAGES (bible)" in txt


def test_free_subject_reaches_choice_prompt():
    """Un beat « choix » (sujet libre) apparaît bien dans le prompt image compilé."""
    script = _script(1)
    doc = scene_plan_to_document(adventure_to_video_plan(script))
    choice_desc = script.rounds[0].choices[0].image_desc
    # le sujet libre est en tête du prompt image du plan choix A.
    choice = next(b for b in doc.bricks
                  if isinstance(b, ClipBrick) and b.id.endswith("choiceA"))
    assert choice.shot is not None and choice.shot.sujet == choice_desc


def test_theme_da_pov_flow_into_style():
    marker = "NEON SYNTHWAVE DA MARKER ZZZ"
    theme = Theme(
        name="custom_test", da=marker, pov="POV FPS", pov_hands="hands",
        no_text="No text.", voice_only_audio="Audio: voice only.",
        ambient_audio="Audio: ambience.", vertical="Vertical 9:16.",
        pace_calm="calm", pace_sudden="sudden", decomposer_tone="neon",
    )
    doc = scene_plan_to_document(adventure_to_video_plan(_script(1), theme=theme))
    assert marker in doc.meta.style_rendu
