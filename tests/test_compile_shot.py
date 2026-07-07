"""Lot F1 — champs métier décomposés : compilateur + recompile + rétro-compat."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.compile_shot import compile_shot_prompt, recompile_document
from src.editor.document import (
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    GenNode,
    ShotBrief,
    ShotCharacter,
    TimelinePlacement,
)
from src.editor.migrations import upgrade_document
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer


def _clip(cid: str, *, shot: ShotBrief | None = None, prompt: str = "") -> ClipBrick:
    return ClipBrick(
        id=cid, kind="photo",
        image=GenNode(model_ref="m", params={"prompt": prompt}),
        shot=shot,
        placement=TimelinePlacement(track=0, start=0.0, duration=3.0),
    )


# -- compilateur --------------------------------------------------------------

def test_compile_regroups_fields_deterministic():
    bible = [CharacterEntry(id="lea", name="Léa", appearance="red-haired teen", wardrobe="blue coat")]
    shot = ShotBrief(
        cadrage="close-up", decor="abandoned subway at night", lumiere="cold flicker",
        characters=[ShotCharacter(ref="lea", expression="terrified", action="running")],
    )
    p1 = compile_shot_prompt(shot, bible)
    p2 = compile_shot_prompt(shot, bible)
    assert p1 == p2
    assert "close-up of Léa (red-haired teen)" in p1
    assert "wearing blue coat, terrified, running" in p1
    assert "in abandoned subway at night" in p1 and "cold flicker" in p1


def test_compile_ignores_empty_and_overrides_wardrobe():
    bible = [CharacterEntry(id="lea", name="Léa", appearance="teen", wardrobe="blue coat")]
    # Surcharge de tenue au niveau du plan ; pas de décor/lumière.
    shot = ShotBrief(characters=[ShotCharacter(ref="lea", wardrobe="red dress", action="waves")])
    out = compile_shot_prompt(shot, bible)
    assert "red dress" in out and "blue coat" not in out
    assert " in " not in out  # pas de décor → pas de « in … »


def test_compile_env_photo_is_decor_led():
    out = compile_shot_prompt(ShotBrief(decor="empty street at dawn"), [])
    assert out == "empty street at dawn"  # pas de sujet → le décor mène, sans « in »


# -- recompile_document + rétro-compat ---------------------------------------

def test_recompile_updates_shot_bricks_only():
    with_shot = _clip("a", shot=ShotBrief(decor="a room"), prompt="STALE")
    legacy = _clip("b", prompt="LEGACY BLOB")  # shot=None
    doc = EditorDocument(bricks=[with_shot, legacy])
    recompile_document(doc)
    assert doc.bricks[0].image.params["prompt"] == "a room"   # recompilé
    assert doc.bricks[1].image.params["prompt"] == "LEGACY BLOB"  # intact (blob)


def test_backward_compat_shot_none_unchanged():
    """INVARIANT : une brique sans `shot` n'est jamais touchée (compile/spec identiques)."""
    doc = EditorDocument(bricks=[_clip("a", prompt="wide shot, cinematic")])
    before = doc.model_dump_json()
    recompile_document(doc)
    assert doc.model_dump_json() == before


def test_v3_doc_upgrades_to_v4_additive():
    raw = {"schema_version": 3, "title": "old", "bricks": [_clip("a", prompt="x").model_dump()]}
    doc = upgrade_document(raw)
    assert doc.schema_version == 4
    assert doc.bible == []
    assert doc.bricks[0].shot is None  # type: ignore[union-attr]


# -- décomposeur → ShotBrief + bible -----------------------------------------

def test_fake_decomposer_builds_shots_and_bible():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    doc = scene_plan_to_document(plan, title="T")
    assert doc.bible and doc.bible[0].name == "Léa"
    clips = [b for b in doc.bricks if isinstance(b, ClipBrick)]
    shots = [c for c in clips if c.shot is not None]
    assert shots  # les plans portent des champs métier
    # Un plan avec personnage → prompt compilé qui cite la bible + reste prêt.
    people_shot = next(c for c in shots if c.shot and c.shot.characters)
    assert "Léa" in people_shot.image.params["prompt"]
    for c in clips:
        assert validate_clip(c) == {}
