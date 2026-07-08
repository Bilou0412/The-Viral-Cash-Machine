"""Les EFFETS de montage sont des DONNÉES IR (TPLM-B) — posés sur le clip, rendus via spec.

Un template doit pouvoir CONTENIR ses effets (countdown flou, zoom, nameplate, eye-open)
comme données, pas via du code impératif hors rail. On vérifie que `document_to_spec`
émet les bons segments `VideoSpec` à partir des marqueurs déclaratifs du `ClipBrick`
(`countdown`, `nameplates`, `intro_eye_open`, `zoom`). Le rendu (`render_moviepy`)
interprète déjà ces segments — donc effet-dans-le-doc = effet-au-rendu.
"""

import pytest

pytest.importorskip("pydantic")

from src.editor.compile_spec import document_to_spec
from src.editor.document import (
    AudioChild,
    ClipBrick,
    CountdownSpec,
    EditorDocument,
    GenNode,
    NameplateBrief,
    TimelinePlacement,
    ZoomSpec,
)
from src.videospec.models import (
    CountdownSegment,
    IntroSegment,
    NarrationSegment,
)


def _photo(id_: str, prompt: str, **kw) -> ClipBrick:
    return ClipBrick(id=id_, kind="photo", image=GenNode(params={"prompt": prompt}), **kw)


def test_countdown_marker_emits_countdown_segment_with_blur():
    doc = EditorDocument(bricks=[
        _photo("timer", "choose your companion",
               countdown=CountdownSpec(blur_radius=22.0, steps=["3", "2", "1"], step_duration=0.7),
               placement=TimelinePlacement(start=0.0, duration=2.1)),
    ])
    seg = document_to_spec(doc).segments[0]
    assert isinstance(seg, CountdownSegment)
    assert seg.blur_radius == 22.0 and seg.steps == ("3", "2", "1")


def test_intro_eye_open_and_nameplates_emit_ir():
    doc = EditorDocument(bricks=[
        _photo("env", "two companions facing you", intro_eye_open=True,
               nameplates=[NameplateBrief(text="Étienne", side="left"),
                           NameplateBrief(text="Marc", side="right")],
               placement=TimelinePlacement(start=0.0, duration=1.5)),
    ])
    seg = document_to_spec(doc).segments[0]
    assert isinstance(seg, IntroSegment)
    assert seg.transition is not None                      # eye-open demandé
    assert [n.text for n in seg.nameplates] == ["Étienne", "Marc"]
    # nameplates ancrées sur une tête détectée (côté gauche/droit).
    assert [n.placement.side for n in seg.nameplates] == ["left", "right"]


def test_nameplates_flow_onto_narration_segment_too():
    doc = EditorDocument(bricks=[
        _photo("shot", "a lone companion", zoom=ZoomSpec(from_scale=1.0, to_scale=1.2),
               nameplates=[NameplateBrief(text="Léa", side="left")],
               children=[AudioChild(id="shot__narr", role="narration",
                                    params={"text": "Tu avances dans le noir."})]),
    ])
    seg = document_to_spec(doc).segments[0]
    assert isinstance(seg, NarrationSegment)
    assert [n.text for n in seg.nameplates] == ["Léa"]
    assert seg.zoom is not None and seg.zoom.scale_to == 1.2


def test_countdown_is_photo_only_and_carries_no_narration():
    with pytest.raises(ValueError):
        ClipBrick(id="bad", kind="video", image=GenNode(),
                  motion=GenNode(), countdown=CountdownSpec())
    with pytest.raises(ValueError):
        _photo("bad2", "x", countdown=CountdownSpec(),
               children=[AudioChild(id="bad2__n", role="narration", params={"text": "hi"})])
