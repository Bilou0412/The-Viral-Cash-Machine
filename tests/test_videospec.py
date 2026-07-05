"""Tests du contrat VideoSpec : round-trip JSON, validation des refs, schéma."""

import json

import pytest

pydantic = pytest.importorskip("pydantic")

from src.videospec import FileAsset, FootageSegment, VideoSpec  # noqa: E402
from src.videospec.builder import legacy_spec  # noqa: E402
from src.videospec.schema import export_schema  # noqa: E402


def test_legacy_spec_is_valid():
    spec = legacy_spec("Karim", "Sofiane")
    assert len(spec.segments) == 4
    assert [s.type for s in spec.segments] == [
        "intro",
        "footage",
        "narration",
        "countdown",
    ]


def test_legacy_spec_without_narration():
    spec = legacy_spec("Karim", "Sofiane", with_narration=False)
    assert [s.type for s in spec.segments] == ["intro", "footage"]


def test_json_round_trip():
    spec = legacy_spec("Karim", "Sofiane")
    payload = spec.model_dump_json()
    restored = VideoSpec.model_validate_json(payload)
    assert restored == spec


def test_unknown_asset_ref_rejected():
    with pytest.raises(Exception) as exc:
        VideoSpec(
            assets=(FileAsset(id="vid", path="video.mp4"),),
            segments=(FootageSegment(video="missing"),),
        )
    assert "missing" in str(exc.value)


def test_duplicate_asset_ids_rejected():
    with pytest.raises(Exception):
        VideoSpec(
            assets=(
                FileAsset(id="vid", path="a.mp4"),
                FileAsset(id="vid", path="b.mp4"),
            ),
            segments=(FootageSegment(video="vid"),),
        )


def test_extra_fields_forbidden():
    """Critique pour le structured output : le LLM ne peut pas halluciner de champs."""
    with pytest.raises(Exception):
        VideoSpec.model_validate(
            {"assets": [], "segments": [], "hallucinated_field": True}
        )


def test_schema_export(tmp_path):
    out = export_schema(str(tmp_path / "videospec.schema.json"))
    with open(out, encoding="utf-8") as fh:
        schema = json.loads(fh.read())
    assert schema["title"] == "VideoSpec"
    assert "$defs" in schema
