"""Tests for the DB-independent studio services (phase U1).

These cover the pure brain reuse — script generation (Fake), the image-first
generation plan, and the cost estimate — with NO network and NO database, so
they hold regardless of the DB layer. The full API integration test lives in
test_studio_api.py.
"""

import pytest

pytest.importorskip("pydantic")

from src.studio.api.services.fakes import FakeAssetProvider  # noqa: E402
from src.studio.api.services.generation_plan import (  # noqa: E402
    estimate_cost,
    plan_episode_assets,
)
from src.studio.api.services.scripting import generate_script  # noqa: E402


@pytest.fixture
def script():
    return generate_script("cave horror", "Étienne", "Marc")


def test_generate_script_uses_fake_offline(script):
    # No OPENAI_API_KEY in test env -> deterministic FakeAdventureDecomposer.
    assert script.char_left_name == "Étienne"
    assert script.char_right_name == "Marc"
    assert len(script.rounds) == 3


def test_plan_is_image_first_with_expected_counts(script):
    plan = plan_episode_assets(script)
    images = [a for a in plan if a.kind == "image"]
    videos = [a for a in plan if a.kind == "video"]
    audio = [a for a in plan if a.kind == "audio"]

    # 3 rounds x (5 beat frames + 2 choice images) + 1 epilogue frame = 22.
    assert len(images) == 22
    # 3 rounds x 5 beats + 1 epilogue = 16 motions.
    assert len(videos) == 16
    # 1 narration track + 3 character lines.
    assert len(audio) == 4


def test_every_video_beat_has_a_preceding_frame(script):
    """Image-first invariant: each *.motion is preceded by its *.frame image."""
    plan = plan_episode_assets(script)
    for i, asset in enumerate(plan):
        if asset.kind == "video":
            assert asset.beat.endswith(".motion")
            assert asset.image_prompt and asset.motion_prompt
            prev = plan[i - 1]
            assert prev.kind == "image"
            assert prev.beat == asset.beat.replace(".motion", ".frame")
            # The motion reuses the frame's image as its source.
            assert prev.image_prompt == asset.image_prompt


def test_estimate_cost_breakdown_and_total(script):
    est = estimate_cost(script)
    kinds = {line.unit_kind for line in est.lines}
    assert kinds == {"image", "second", "kchar"}
    assert est.total_usd > 0
    # Draft is cheaper than final (video multiplier < 1).
    assert estimate_cost(script, draft=True).total_usd < est.total_usd


def test_fake_provider_records_calls_no_network():
    fake = FakeAssetProvider()
    url = fake.generate_image("a dark cave", "2K", "9:16")
    assert url.startswith("https://fake.local/")
    assert fake.image_calls == [("a dark cave", "2K", "9:16")]
    vurl = fake.animate_video("move", url, 7, "9:16", "720p")
    assert vurl.endswith(".mp4")
    assert fake.video_calls[0]["image"] == url
