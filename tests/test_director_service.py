"""TPLM-D — service réalisateur : assemble une PARTIE (description NL) et l'appende
au document, sur le rail v5, offline (Fake). Prouve que le maillon débranché de TPLM-C
est désormais invocable côté studio et que la forme reste valide/compilable."""

import pytest

pytest.importorskip("pydantic")

from src.editor.compile_spec import document_to_spec
from src.editor.document import ClipBrick
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.studio.api.services.director import assemble_part
from src.videospec.models import CountdownSegment, IntroSegment

_DESC = (
    "Une intro : Étienne et Marc, deux compagnons dans le noir ; chacun te parle "
    "en face caméra pour te convaincre, puis on te demande de choisir."
)


def _base_doc():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    return scene_plan_to_document(plan, title="Ma vidéo")


def _end(doc) -> float:
    ends = [
        b.placement.start + b.placement.duration
        for b in doc.bricks
        if isinstance(b, ClipBrick) and b.placement.duration > 0
    ]
    return max(ends) if ends else 0.0


def test_assemble_part_appends_fragment_after_timeline_and_stays_valid():
    doc = _base_doc()
    n_before, end_before = len(doc.bricks), _end(doc)
    out = assemble_part(doc, _DESC, part="intro")  # Fake (pas de clé OpenAI)

    added = [
        b for b in out.bricks
        if isinstance(b, ClipBrick) and b.id.startswith("intro")
    ]
    assert len(out.bricks) > n_before and added  # le fragment est ajouté
    # Posé À LA SUITE de la timeline existante (co-construction incrémentale).
    assert all(b.placement.start >= end_before - 1e-6 for b in added)
    # ids uniques : garanti par la revalidation EditorDocument (sinon ValueError).
    ids = [b.id for b in out.bricks]
    assert len(ids) == len(set(ids))
    # Briques structurées (ShotBrief présent) — jamais de blob shot=None.
    assert all(b.shot is not None for b in added)


def test_assembled_fragment_compiles_to_ir_effects():
    doc = assemble_part(_base_doc(), _DESC, part="intro")
    kinds = [type(s).__name__ for s in document_to_spec(doc).segments]
    assert IntroSegment.__name__ in kinds        # établissement eye-open (effet catalogue)
    assert CountdownSegment.__name__ in kinds     # countdown flou (effet catalogue)


def test_assemble_twice_keeps_ids_unique():
    doc = _base_doc()
    doc = assemble_part(doc, _DESC, part="intro")
    doc = assemble_part(doc, _DESC, part="intro")  # même part → suffixage, pas de collision
    ids = [b.id for b in doc.bricks]
    assert len(ids) == len(set(ids))
