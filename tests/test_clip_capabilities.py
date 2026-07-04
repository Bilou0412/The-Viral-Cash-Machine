"""Tests du pont ClipBrick ↔ contrats de capacité (B2) — pur, hors-ligne."""

import pytest

pytest.importorskip("pydantic")

from src.editor import ClipBrick
from src.editor.capabilities import (
    clip_is_ready,
    clip_node_kinds,
    validate_clip,
)


def _ready_video() -> ClipBrick:
    return ClipBrick(
        id="v1",
        kind="video",
        image={"params": {"prompt": "a cave"}},
        motion={"params": {"prompt": "walk", "duration": 5}},
        children=[{"id": "d1", "role": "dialogue", "params": {"text": "salut"}}],
    )


def test_ready_video_clip_has_no_issues():
    clip = _ready_video()
    assert validate_clip(clip) == {}
    assert clip_is_ready(clip) is True


def test_image_prompt_missing_reported():
    clip = ClipBrick(id="v", kind="video", image={"params": {}}, motion={"params": {"prompt": "x", "duration": 3}})
    assert validate_clip(clip)["image"] == ["prompt"]


def test_motion_image_is_supplied_by_sibling_not_required():
    """Le motion ne porte pas `image` : il est fourni par le nœud frère."""
    clip = ClipBrick(
        id="v",
        kind="video",
        image={"params": {"prompt": "p"}},
        motion={"params": {"duration": 4}},  # pas de `image` ici → OK
    )
    assert "motion" not in validate_clip(clip)


def test_motion_prompt_falls_back_to_image_prompt():
    clip = ClipBrick(
        id="v",
        kind="video",
        image={"params": {"prompt": "p"}},
        motion={"params": {"duration": 4}},  # pas de prompt motion → repli image
    )
    assert validate_clip(clip) == {}


def test_duration_from_placement_satisfies_motion():
    clip = ClipBrick(
        id="v",
        kind="video",
        image={"params": {"prompt": "p"}},
        motion={"params": {"prompt": "m"}},  # pas de duration
        placement={"track": 0, "start": 0.0, "duration": 6.0},
    )
    assert validate_clip(clip) == {}


def test_duration_missing_everywhere_reported():
    clip = ClipBrick(
        id="v",
        kind="video",
        image={"params": {"prompt": "p"}},
        motion={"params": {"prompt": "m"}},  # ni duration ici ni dans placement
    )
    assert validate_clip(clip)["motion"] == ["duration"]


def test_narration_child_requires_voice_id():
    clip = ClipBrick(
        id="p",
        kind="photo",
        image={"params": {"prompt": "ruins"}},
        children=[{"id": "n1", "role": "narration", "params": {"text": "le silence"}}],
    )
    assert validate_clip(clip)["child:n1"] == ["voice_id"]


def test_dialogue_child_voice_id_optional():
    clip = ClipBrick(
        id="p",
        kind="photo",
        image={"params": {"prompt": "x"}},
        children=[{"id": "d1", "role": "dialogue", "params": {"text": "hello"}}],
    )
    assert validate_clip(clip) == {}


def test_child_missing_text_reported():
    clip = ClipBrick(
        id="p",
        kind="photo",
        image={"params": {"prompt": "x"}},
        children=[{"id": "n1", "role": "narration", "params": {"voice_id": "V"}}],
    )
    assert validate_clip(clip)["child:n1"] == ["text"]


def test_voice_id_alias_satisfies():
    clip = ClipBrick(
        id="p",
        kind="photo",
        image={"params": {"prompt": "x"}},
        children=[{"id": "n1", "role": "narration", "params": {"text": "t", "voice": "V"}}],
    )
    assert validate_clip(clip) == {}  # `voice` est un alias de `voice_id`


def test_photo_zoom_without_narration_is_not_ready():
    """Invariant : ce que le compilateur refuserait est jugé non-prêt en amont."""
    clip = ClipBrick(
        id="p", kind="photo", image={"params": {"prompt": "x"}},
        zoom={"from_scale": 1.0, "to_scale": 1.2},
    )
    assert validate_clip(clip) == {"zoom": ["narration"]}
    assert clip_is_ready(clip) is False
    # avec un enfant audio, la photo zoomée redevient rendable
    ok = ClipBrick(
        id="p2", kind="photo", image={"params": {"prompt": "x"}},
        zoom={"from_scale": 1.0, "to_scale": 1.2},
        children=[{"id": "n", "role": "narration", "params": {"text": "t", "voice_id": "V"}}],
    )
    assert clip_is_ready(ok) is True


def test_empty_string_prompt_counts_as_missing():
    clip = ClipBrick(id="v", kind="video", image={"params": {"prompt": "   "}},
                     motion={"params": {"prompt": "m", "duration": 3}})
    assert validate_clip(clip)["image"] == ["prompt"]


def test_empty_string_child_text_counts_as_missing():
    clip = ClipBrick(id="p", kind="photo", image={"params": {"prompt": "x"}},
                     children=[{"id": "n", "role": "dialogue", "params": {"text": ""}}])
    assert validate_clip(clip)["child:n"] == ["text"]


def test_text_alias_satisfies():
    clip = ClipBrick(id="p", kind="photo", image={"params": {"prompt": "x"}},
                     children=[{"id": "d", "role": "dialogue", "params": {"input_text": "salut"}}])
    assert validate_clip(clip) == {}  # `input_text` est un alias de `text`


def test_node_kinds_map_for_form_lookup():
    clip = _ready_video()
    assert clip_node_kinds(clip) == {"image": "image", "motion": "video", "child:d1": "voice"}
    photo = ClipBrick(id="p", kind="photo", image={"params": {"prompt": "x"}})
    assert clip_node_kinds(photo) == {"image": "image"}
