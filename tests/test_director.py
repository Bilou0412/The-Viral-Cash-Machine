"""Le RÉALISATEUR assemble une partie depuis une description NL (TPLM-C).

Cœur de la co-construction : une description en langage naturel + le catalogue d'effets
→ un `FragmentPlan` (beats à effets) → des `ClipBrick` v5 (effets posés en IR) →
`document_to_spec` émet les bons segments. On prouve la boucle sur l'intro de l'exemple,
offline (FakeDirectorAgent). L'agent ne pose QUE des effets présents dans la palette.
"""

import pytest

pytest.importorskip("pydantic")

from src.editor.compile_spec import document_to_spec
from src.editor.document import ClipBrick, EditorDocument
from src.features.crew import fragment_to_bricks
from src.features.crew.fake_director_agent import FakeDirectorAgent
from src.studio.api.services.context import effect_cards
from src.videospec.models import (
    CountdownSegment,
    FootageSegment,
    IntroSegment,
    NarrationSegment,
)

_EFFECTS = [e.name for e in effect_cards()]
_DESC = ("Une intro : Étienne et Marc, deux compagnons dans le noir ; chacun te parle "
         "en face caméra pour te convaincre de le choisir, puis on te demande de choisir.")


def _fragment():
    return FakeDirectorAgent().assemble(description=_DESC, part="intro", effects=_EFFECTS)


def test_director_extracts_names_and_places_effects():
    plan = _fragment()
    assert plan.part == "intro" and plan.beats
    env = plan.beats[0]
    assert env.eye_open and [n.text for n in env.nameplates] == ["Étienne", "Marc"]
    assert any(b.countdown for b in plan.beats)          # écran timer posé
    assert not any(b.countdown and b.narration_fr for b in plan.beats)  # timer sans narration


def test_director_only_uses_effects_from_the_catalogue():
    """Sans timer/eye-open dans la palette, l'agent ne les pose pas."""
    plan = FakeDirectorAgent().assemble(description=_DESC, part="intro", effects=[])
    assert not any(b.eye_open or b.countdown for b in plan.beats)


def test_fragment_compiles_to_the_intro_as_ir_segments():
    """Le fragment → briques v5 → spec : l'intro exacte, entièrement en IR."""
    doc = EditorDocument(bricks=fragment_to_bricks(_fragment()))
    # Briques structurées (shot présent) — pas des blobs.
    assert all(b.shot is not None for b in doc.bricks if isinstance(b, ClipBrick))
    kinds = [type(s).__name__ for s in document_to_spec(doc).segments]
    assert kinds[0] == IntroSegment.__name__          # établissement eye-open
    assert kinds.count(FootageSegment.__name__) == 2  # les 2 compagnons face caméra
    assert NarrationSegment.__name__ in kinds         # « choisis A ou B »
    assert kinds[-1] == CountdownSegment.__name__     # countdown flou final


def test_intro_segment_carries_eye_open_and_nameplates():
    doc = EditorDocument(bricks=fragment_to_bricks(_fragment()))
    intro = document_to_spec(doc).segments[0]
    assert isinstance(intro, IntroSegment)
    assert intro.transition is not None
    assert [n.text for n in intro.nameplates] == ["Étienne", "Marc"]


def test_beat_id_coerced_from_int():
    """Robustesse LLM (trouvée en test réel) : GPT renvoie l'id en entier → coerce en str."""
    from src.features.crew.model import BeatPlan, FragmentPlan

    plan = FragmentPlan.model_validate({"part": "intro", "beats": [{"id": 1, "kind": "photo"}]})
    assert plan.beats[0].id == "1"
    assert BeatPlan.model_validate({"id": 3}).id == "3"
