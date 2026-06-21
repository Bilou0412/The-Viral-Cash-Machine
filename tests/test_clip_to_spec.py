"""Tests du compilateur ClipBrick → VideoSpec (B1) — pur, hors-ligne."""

import pytest

pytest.importorskip("pydantic")

from src.editor import ClipBrick, EditorDocument, document_to_spec  # noqa: E402
from src.editor.capabilities import clip_is_ready  # noqa: E402
from src.videospec.models import (  # noqa: E402
    FootageSegment,
    ImageAsset,
    IntroSegment,
    NarrationSegment,
    VideoAsset,
    VoiceAsset,
)


def _video_clip(**over) -> dict:
    base = {
        "id": "v1",
        "type": "clip",
        "kind": "video",
        "image": {"model_ref": "bytedance/seedream-4.5", "params": {"prompt": "a cave"}},
        "motion": {"model_ref": "prunaai/p-video", "params": {"duration": 5, "prompt": "walk"}},
        "children": [
            {"id": "d1", "role": "dialogue", "params": {"text": "qui est là", "voice_id": "X"}}
        ],
        "placement": {"track": 0, "start": 0.0, "duration": 5.0},
    }
    base.update(over)
    return base


def test_video_clip_emits_footage_with_image_video_voice():
    spec = document_to_spec(EditorDocument(bricks=[_video_clip()]))
    by_id = {a.id: a for a in spec.assets}
    assert isinstance(by_id["v1__img"], ImageAsset)
    assert by_id["v1__img"].prompt == "a cave"
    assert isinstance(by_id["v1__voice"], VoiceAsset)
    assert by_id["v1__voice"].voice_id == "X"
    vid = by_id["v1__vid"]
    assert isinstance(vid, VideoAsset)
    assert vid.image == "v1__img" and vid.audio == "v1__voice"
    assert vid.duration == 5.0
    assert len(spec.segments) == 1
    seg = spec.segments[0]
    assert isinstance(seg, FootageSegment)
    assert seg.video == "v1__vid"
    assert seg.subtitles is not None and seg.subtitles.source == "v1__voice"


def test_video_clip_without_audio_child():
    clip = _video_clip(children=[])
    spec = document_to_spec(EditorDocument(bricks=[clip]))
    vid = next(a for a in spec.assets if isinstance(a, VideoAsset))
    assert vid.audio is None
    assert isinstance(spec.segments[0], FootageSegment)
    assert spec.segments[0].subtitles is None


def test_photo_with_narration_emits_narration_segment_with_zoom():
    clip = {
        "id": "p1",
        "type": "clip",
        "kind": "photo",
        "image": {"params": {"prompt": "ruins"}},
        "zoom": {"from_scale": 1.0, "to_scale": 1.3},
        "children": [{"id": "n1", "role": "narration", "params": {"text": "le silence"}}],
        "placement": {"track": 0, "start": 0.0, "duration": 4.0},
    }
    spec = document_to_spec(EditorDocument(bricks=[clip]))
    seg = spec.segments[0]
    assert isinstance(seg, NarrationSegment)
    assert seg.background == "p1__img" and seg.audio == "p1__voice"
    assert seg.zoom is not None and seg.zoom.scale_to == 1.3


def test_photo_without_audio_emits_intro_still():
    clip = {
        "id": "p2",
        "type": "clip",
        "kind": "photo",
        "image": {"params": {"prompt": "a wall"}},
        "placement": {"track": 0, "start": 0.0, "duration": 2.0},
    }
    spec = document_to_spec(EditorDocument(bricks=[clip]))
    seg = spec.segments[0]
    assert isinstance(seg, IntroSegment)
    assert seg.background == "p2__img"
    assert seg.transition is None
    assert seg.duration == 2.0


def test_photo_zoom_without_narration_raises():
    clip = {
        "id": "p3",
        "type": "clip",
        "kind": "photo",
        "image": {"params": {"prompt": "x"}},
        "zoom": {"from_scale": 1.0, "to_scale": 1.2},
    }
    with pytest.raises(ValueError, match="zoom"):
        document_to_spec(EditorDocument(bricks=[clip]))


def test_multiple_audio_children_raise():
    clip = _video_clip(
        children=[
            {"id": "a", "role": "narration", "params": {"text": "1"}},
            {"id": "b", "role": "dialogue", "params": {"text": "2"}},
        ]
    )
    with pytest.raises(ValueError, match="audio"):
        document_to_spec(EditorDocument(bricks=[clip]))


def test_clips_ordered_by_start():
    late = _video_clip(id="late", children=[], placement={"track": 0, "start": 5.0, "duration": 3.0})
    early = _video_clip(id="early", children=[], placement={"track": 0, "start": 0.0, "duration": 3.0})
    spec = document_to_spec(EditorDocument(bricks=[late, early]))
    assert [s.video for s in spec.segments] == ["early__vid", "late__vid"]


def test_legacy_flat_bricks_ignored():
    doc = EditorDocument(
        bricks=[
            _video_clip(),
            {"id": "old", "type": "image", "params": {"prompt": "legacy"}},
        ]
    )
    spec = document_to_spec(doc)
    # un seul clip compilé ; la brique plate est ignorée (chemin resolve.py).
    assert len(spec.segments) == 1
    assert all(not a.id.startswith("old") for a in spec.assets)


def test_canvas_is_reused_from_document():
    spec = document_to_spec(EditorDocument(bricks=[]))
    assert (spec.canvas.width, spec.canvas.height) == (1080, 1920)
    assert spec.assets == () and spec.segments == ()


def test_child_text_alias_not_dropped_by_compiler():
    """Un enfant renseigné via l'alias `input_text` ne compile PAS en voix vide."""
    clip = {
        "id": "p", "type": "clip", "kind": "photo",
        "image": {"params": {"prompt": "x"}},
        "children": [{"id": "n", "role": "narration",
                      "params": {"input_text": "le silence", "voice": "V"}}],
    }
    spec = document_to_spec(EditorDocument(bricks=[clip]))
    voice = next(a for a in spec.assets if isinstance(a, VoiceAsset))
    assert voice.text == "le silence"  # alias honoré, pas de texte vide
    assert voice.voice_id == "V"        # alias `voice` → voice_id


def test_duration_alias_num_frames_honored():
    clip = _video_clip(motion={"params": {"prompt": "m", "num_frames": 8}}, placement={"track": 0, "start": 0.0, "duration": 0.0})
    spec = document_to_spec(EditorDocument(bricks=[clip]))
    vid = next(a for a in spec.assets if isinstance(a, VideoAsset))
    assert vid.duration == 8.0


# -- INVARIANT de cohérence validate_clip ↔ compilateur ---------------------

_INVARIANT_CLIPS = [
    {"id": "v", "type": "clip", "kind": "video", "image": {"params": {"prompt": "p"}},
     "motion": {"params": {"prompt": "m", "duration": 3}}},
    {"id": "vfb", "type": "clip", "kind": "video", "image": {"params": {"prompt": "p"}},
     "motion": {"params": {"duration": 3}}},  # prompt motion via repli image
    {"id": "pn", "type": "clip", "kind": "photo", "image": {"params": {"prompt": "p"}},
     "zoom": {"from_scale": 1.0, "to_scale": 1.2},
     "children": [{"id": "n", "role": "narration", "params": {"text": "t", "voice_id": "V"}}]},
    {"id": "pf", "type": "clip", "kind": "photo", "image": {"params": {"prompt": "p"}}},
    {"id": "alias", "type": "clip", "kind": "photo", "image": {"params": {"prompt": "p"}},
     "children": [{"id": "d", "role": "dialogue", "params": {"input_text": "hi"}}]},
]


@pytest.mark.parametrize("raw", _INVARIANT_CLIPS, ids=lambda r: r["id"])
def test_ready_implies_compile_succeeds(raw):
    """clip_is_ready(c) ⟹ document_to_spec(c) réussit sans lever."""
    clip = EditorDocument(bricks=[raw]).bricks[0]
    if clip_is_ready(clip):
        spec = document_to_spec(EditorDocument(bricks=[clip]))
        assert len(spec.segments) == 1
        # aucun asset au prompt/texte vide n'est produit
        for a in spec.assets:
            if isinstance(a, ImageAsset):
                assert a.prompt.strip() != ""
            if isinstance(a, VoiceAsset):
                assert a.text.strip() != ""
