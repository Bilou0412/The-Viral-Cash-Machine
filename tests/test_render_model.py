"""Tests du contrat RenderModel (lu par Remotion)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.render_model import RenderClip, RenderModel, SubtitleWord


def _model() -> RenderModel:
    return RenderModel(
        clips=(
            RenderClip(
                id="c0", media="image", src="/api/assets/1/file", start=0.0, duration=3.0
            ),
            RenderClip(
                id="c1", media="video", src="/api/assets/2/file", start=3.0, duration=5.0,
                subtitles=(SubtitleWord(text="tu", start=3.1, end=3.4),),
            ),
            RenderClip(
                id="c2", media="text", start=0.0, duration=2.0, z=10,
                text="Round 1", style={"color": "white", "size": 72},
            ),
        ),
        total_duration=8.0,
    )


def test_construct_and_canvas_default_vertical():
    m = _model()
    assert (m.canvas.width, m.canvas.height) == (1080, 1920)
    assert m.version == "1.0"
    assert len(m.clips) == 3


def test_json_round_trip():
    m = _model()
    assert RenderModel.model_validate_json(m.model_dump_json()) == m


def test_frozen_and_strict():
    m = _model()
    with pytest.raises(Exception):
        m.total_duration = 1.0  # type: ignore[misc]
    with pytest.raises(Exception):
        RenderModel(clips=(), total_duration=0.0, hallucinated=True)
