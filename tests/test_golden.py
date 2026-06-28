"""Characterization test against the frozen golden (ARCHITECTURE_PLAN.md, verification #2).

Two modes:

* No candidate  -> self-integrity: the frozen golden still matches its own recorded
  invariants. Guards against accidental corruption of the fixture (cheap, always runs).

* With candidate -> regression check: point GOLDEN_CANDIDATE at an export instance dir
  freshly produced after a refactor step, e.g.

      GOLDEN_CANDIDATE=exports/default_project/20260610_101500 pytest tests/test_golden.py

  and the candidate's final_video.mp4 / metadata.json are diffed against the golden:
  structure (exact), duration + segment plan (tolerance), SSIM (tolerance), stable
  metadata keys (exact). Any drift is a regression to explain before continuing.

Needs only ffmpeg/ffprobe on PATH + pytest. No moviepy / GPU / Replicate / OpenAI.
"""
from __future__ import annotations

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden_tools as gt  # noqa: E402

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "golden")
GOLDEN_VIDEO = os.path.join(GOLDEN_DIR, "final_video.mp4")
GOLDEN_META = os.path.join(GOLDEN_DIR, "metadata.json")
GOLDEN_INVARIANTS = os.path.join(GOLDEN_DIR, "invariants.json")

# Tolerances: encoders jitter the tail frame and re-quantize pixels; structure must
# still hold and the picture must stay perceptually identical.
DURATION_TOL_S = 0.20
SSIM_MIN = 0.95

CANDIDATE_DIR = os.environ.get("GOLDEN_CANDIDATE")
requires_candidate = pytest.mark.skipif(
    not CANDIDATE_DIR, reason="set GOLDEN_CANDIDATE=<export instance dir> to diff a fresh render"
)

# These probes shell out to ffprobe/ffmpeg; skip cleanly where the binary is
# absent (e.g. the ephemeral web container) instead of failing the cheap suite.
requires_ffprobe = pytest.mark.skipif(
    shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None,
    reason="ffprobe/ffmpeg not on PATH",
)


@pytest.fixture(scope="module")
def invariants() -> dict:
    if not os.path.exists(GOLDEN_INVARIANTS):
        pytest.skip("golden not captured yet (run tests/capture_golden.py)")
    return gt.load_json(GOLDEN_INVARIANTS)


# --- golden self-integrity (no candidate needed) --------------------------

@requires_ffprobe
def test_golden_video_matches_recorded_probe(invariants):
    probe = gt.probe_to_dict(gt.probe_video(GOLDEN_VIDEO))
    assert probe == invariants["final_video"]


@requires_ffprobe
def test_golden_key_frames_unchanged(invariants):
    """Re-extract each key frame from the frozen video and confirm its checksum."""
    for name, rec in invariants["key_frames"].items():
        png = os.path.join(GOLDEN_DIR, f"_selfcheck_{name}.png")
        try:
            gt.extract_frame(GOLDEN_VIDEO, rec["timestamp"], png)
            assert gt.sha256_file(png) == rec["sha256"], f"key frame '{name}' drifted"
        finally:
            if os.path.exists(png):
                os.remove(png)


def test_golden_metadata_unchanged(invariants):
    assert gt.sha256_file(GOLDEN_META) == invariants["metadata_sha256"]


# --- candidate regression check (post-refactor render) --------------------

@requires_candidate
def test_candidate_structure_and_duration(invariants):
    cand_video = os.path.join(CANDIDATE_DIR, "final_video.mp4")
    assert os.path.exists(cand_video), f"candidate missing {cand_video}"
    cand = gt.probe_video(cand_video)
    gold = invariants["final_video"]

    assert cand.codec == gold["codec"]
    assert (cand.width, cand.height) == (gold["width"], gold["height"])
    assert cand.fps == pytest.approx(gold["fps"], abs=0.01)
    assert cand.duration == pytest.approx(gold["duration"], abs=DURATION_TOL_S)

    cand_plan = gt.segment_plan(
        os.path.join(CANDIDATE_DIR, "video.mp4"),
        os.path.join(CANDIDATE_DIR, "narrator.mp3"),
    )
    assert [s["name"] for s in cand_plan] == [s["name"] for s in invariants["segment_plan"]]
    for c, g in zip(cand_plan, invariants["segment_plan"]):
        assert c["duration"] == pytest.approx(g["duration"], abs=DURATION_TOL_S), c["name"]


@requires_candidate
def test_candidate_visually_matches_golden():
    cand_video = os.path.join(CANDIDATE_DIR, "final_video.mp4")
    score = gt.ssim(cand_video, GOLDEN_VIDEO)
    assert score >= SSIM_MIN, f"SSIM {score:.4f} < {SSIM_MIN} — visual regression"


@requires_candidate
def test_candidate_stable_metadata_matches_golden():
    cand = gt.stable_metadata(gt.load_json(os.path.join(CANDIDATE_DIR, "metadata.json")))
    gold = gt.stable_metadata(gt.load_json(GOLDEN_META))
    assert cand == gold
