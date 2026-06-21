"""Tests du modèle EditorDocument (E1) — authoring de l'éditeur timeline."""

import pytest

pytest.importorskip("pydantic")

from src.editor import (  # noqa: E402
    ClipBrick,
    EditorDocument,
    GenerativeBrick,
    MediaBrick,
    TextBrick,
    upgrade_document,
)
from src.editor.document import SCHEMA_VERSION  # noqa: E402


def _doc() -> EditorDocument:
    return EditorDocument(
        title="Mon montage",
        global_context={"text": "une nuit dans la mine", "art_direction": "horreur"},
        tracks=[{"index": 0, "role": "video"}, {"index": 1, "role": "audio"}],
        bricks=[
            {
                "id": "img1",
                "type": "image",
                "model_ref": "bytedance/seedream-4.5",
                "params": {"prompt": "a dark cave"},
                "placement": {"track": 0, "start": 0.0, "duration": 3.0},
            },
            {
                "id": "vid1",
                "type": "video",
                "model_ref": "prunaai/p-video",
                "params": {"prompt": "walk", "duration": 5, "image": "{brick:img1}"},
                "placement": {"track": 0, "start": 3.0, "duration": 5.0},
                "layers": [
                    {"type": "narration", "payload": {"brick_ref": "narr1"}},
                    {"type": "text", "payload": {"content": "Round 1"}},
                ],
            },
            {
                "id": "narr1",
                "type": "voice",
                "model_ref": "minimax/speech-2.8-turbo",
                "params": {"text": "tu avances", "voice_id": "X"},
                "placement": {"track": 1, "start": 3.0, "duration": 5.0},
            },
        ],
    )


def test_discriminated_union_resolves_brick_types():
    d = _doc()
    by_id = {b.id: b for b in d.bricks}
    assert isinstance(by_id["img1"], GenerativeBrick)
    assert by_id["img1"].type == "image"
    assert by_id["vid1"].type == "video"
    assert by_id["narr1"].type == "voice"


def test_media_and_text_bricks():
    d = EditorDocument(
        bricks=[
            {"id": "m", "type": "media", "source_path": "/tmp/x.png"},
            {"id": "t", "type": "text", "payload": {"content": "Salut"}},
        ]
    )
    by_id = {b.id: b for b in d.bricks}
    assert isinstance(by_id["m"], MediaBrick)
    assert isinstance(by_id["t"], TextBrick)


def test_params_are_free_form():
    """Les params d'une brique générative ne sont PAS contraints par pydantic."""
    b = GenerativeBrick(
        id="x", type="image", params={"anything": 1, "nested": {"a": [1, 2]}}
    )
    assert b.params["nested"]["a"] == [2, 1][::-1]


def test_json_round_trip():
    d = _doc()
    restored = EditorDocument.model_validate_json(d.model_dump_json())
    assert restored == d


def test_duplicate_brick_ids_rejected():
    with pytest.raises(Exception):
        EditorDocument(
            bricks=[
                {"id": "dup", "type": "image"},
                {"id": "dup", "type": "voice"},
            ]
        )


def test_narration_layer_dangling_ref_rejected():
    with pytest.raises(Exception):
        EditorDocument(
            bricks=[
                {
                    "id": "vid",
                    "type": "video",
                    "layers": [
                        {"type": "narration", "payload": {"brick_ref": "ghost"}}
                    ],
                }
            ]
        )


def test_extra_fields_forbidden():
    with pytest.raises(Exception):
        EditorDocument(bricks=[], hallucinated=True)


def test_upgrade_document_sets_schema_version():
    raw = {"title": "vieux", "bricks": []}  # sans schema_version
    d = upgrade_document(raw)
    assert d.schema_version == SCHEMA_VERSION
    assert d.title == "vieux"


def test_canvas_default_is_vertical():
    d = EditorDocument()
    assert (d.canvas.width, d.canvas.height) == (1080, 1920)


# --- ClipBrick : brique composite VIDÉO/PHOTO (B0) -------------------------


def _video_clip() -> dict:
    return {
        "id": "clip1",
        "type": "clip",
        "kind": "video",
        "image": {"model_ref": "bytedance/seedream-4.5", "params": {"prompt": "a cave"}},
        "motion": {"model_ref": "prunaai/p-video", "params": {"duration": 5}},
        "children": [
            {
                "id": "n1",
                "role": "narration",
                "model_ref": "minimax/speech-2.8-turbo",
                "params": {"text": "tu avances", "voice_id": "X"},
            },
            {"id": "d1", "role": "dialogue", "params": {"text": "qui est là ?"}},
        ],
        "placement": {"track": 0, "start": 0.0, "duration": 5.0},
    }


def test_clip_brick_discriminated_in_document():
    d = EditorDocument(bricks=[_video_clip()])
    clip = d.bricks[0]
    assert isinstance(clip, ClipBrick)
    assert clip.kind == "video"
    assert clip.image.params["prompt"] == "a cave"
    assert clip.motion is not None and clip.motion.params["duration"] == 5
    assert [c.role for c in clip.children] == ["narration", "dialogue"]


def test_clip_brick_json_round_trip():
    d = EditorDocument(bricks=[_video_clip()])
    restored = EditorDocument.model_validate_json(d.model_dump_json())
    assert restored == d


def test_photo_clip_with_zoom():
    clip = ClipBrick(
        id="p1",
        kind="photo",
        image={"model_ref": "bytedance/seedream-4.5", "params": {"prompt": "ruins"}},
        zoom={"from_scale": 1.0, "to_scale": 1.3},
    )
    assert clip.zoom is not None and clip.zoom.to_scale == 1.3
    assert clip.motion is None


def test_photo_clip_rejects_motion():
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", motion={"model_ref": "prunaai/p-video"})


def test_video_clip_rejects_zoom():
    with pytest.raises(Exception):
        ClipBrick(id="v", kind="video", zoom={"from_scale": 1.0, "to_scale": 1.2})


def test_clip_duplicate_child_ids_rejected():
    with pytest.raises(Exception):
        ClipBrick(
            id="v",
            kind="video",
            children=[
                {"id": "dup", "role": "narration"},
                {"id": "dup", "role": "dialogue"},
            ],
        )


def test_v1_flat_bricks_still_valid_under_v2():
    """Additif : un doc v1 (briques plates) se charge tel quel sous SCHEMA_VERSION 2."""
    raw = {
        "schema_version": 1,
        "title": "legacy",
        "bricks": [
            {"id": "img1", "type": "image", "model_ref": "x", "params": {"prompt": "p"}},
            {"id": "narr1", "type": "voice", "params": {"text": "t"}},
        ],
    }
    d = upgrade_document(raw)
    assert d.schema_version == SCHEMA_VERSION == 2
    by_id = {b.id: b for b in d.bricks}
    assert isinstance(by_id["img1"], GenerativeBrick)


def test_clip_and_flat_bricks_coexist():
    d = EditorDocument(
        bricks=[
            _video_clip(),
            {"id": "old", "type": "image", "params": {"prompt": "legacy"}},
        ]
    )
    kinds = {type(b).__name__ for b in d.bricks}
    assert kinds == {"ClipBrick", "GenerativeBrick"}


# --- Durcissement B0 (revue multi-agents) ---------------------------------


def test_inf_nan_floats_rejected():
    """inf/NaN sérialisent en null → doc irrechargeable : rejet à la construction."""
    for bad in (float("inf"), float("nan")):
        with pytest.raises(Exception):
            ClipBrick(id="p", kind="photo", zoom={"from_scale": 1.0, "to_scale": bad})
        with pytest.raises(Exception):
            ClipBrick(id="p", kind="photo", placement={"duration": bad})


def test_numeric_bounds_enforced():
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", placement={"duration": -1.0})
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", placement={"track": -1})
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", zoom={"from_scale": 0.0, "to_scale": 1.2})
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", zoom={"from_scale": 1.0, "to_scale": 1.2, "focus_x": 9.0})


def test_empty_ids_rejected():
    with pytest.raises(Exception):
        ClipBrick(id="", kind="photo")
    with pytest.raises(Exception):
        ClipBrick(id="p", kind="photo", children=[{"id": "", "role": "narration"}])
