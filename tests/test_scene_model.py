"""Phase 0 — l'index de scènes (v3) est une MÉTADONNÉE : invisible au rendu,
migration additive, validation lenient. Pur, hors-ligne."""

import pytest

pytest.importorskip("pydantic")

from src.editor import EditorDocument, document_to_spec
from src.editor.document import SCHEMA_VERSION
from src.editor.migrations import upgrade_document


def _clip(cid: str, start: float) -> dict:
    return {
        "id": cid,
        "type": "clip",
        "kind": "video",
        "image": {"params": {"prompt": f"env {cid}"}},
        "motion": {"params": {"prompt": "move", "duration": 4}},
        "children": [{"id": f"{cid}_n", "role": "narration", "params": {"text": "t"}}],
        "placement": {"track": 0, "start": start, "duration": 4.0},
    }


def test_scenes_are_metadata_videospec_identical():
    """Un doc scéné et le même doc sans scènes → VideoSpec byte-identique."""
    bricks = [_clip("a", 0.0), _clip("b", 4.0)]
    plain = EditorDocument(bricks=bricks)
    scened = EditorDocument(
        bricks=bricks,
        scenes=[
            {
                "id": "s1",
                "title": "Scène 1",
                "environment_photo_ref": "a",
                "shot_ids": ["a", "b"],
            }
        ],
    )
    assert document_to_spec(plain).model_dump() == document_to_spec(scened).model_dump()


def test_scene_ref_unknown_brick_raises():
    with pytest.raises(ValueError, match="brique inconnue"):
        EditorDocument(bricks=[_clip("a", 0.0)], scenes=[{"id": "s", "shot_ids": ["ghost"]}])


def test_scene_ids_must_be_unique():
    with pytest.raises(ValueError, match="scènes dupliqués"):
        EditorDocument(
            bricks=[_clip("a", 0.0)],
            scenes=[{"id": "dup", "shot_ids": ["a"]}, {"id": "dup", "shot_ids": ["a"]}],
        )


def test_v2_doc_upgrades_to_v3_with_empty_scenes():
    """Un document persisté en v2 (sans `scenes`) se charge en v3 avec scenes=[]."""
    raw = {"schema_version": 2, "title": "vieux", "bricks": [_clip("a", 0.0)]}
    doc = upgrade_document(raw)
    assert doc.schema_version == SCHEMA_VERSION == 3
    assert doc.scenes == []
    assert len(doc.bricks) == 1
