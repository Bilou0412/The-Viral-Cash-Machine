"""Tests for the DB-independent studio services (phase U1).

These cover the pure brain reuse — script generation (Fake), the image-first
generation plan, and the cost estimate — with NO network and NO database, so
they hold regardless of the DB layer. The full API integration test lives in
test_studio_api.py.
"""

import os

import pytest

pytest.importorskip("pydantic")

from src.studio.api.services.fakes import FakeAssetProvider  # noqa: E402
from src.studio.api.services.generation_plan import (  # noqa: E402
    estimate_cost,
    plan_episode_assets,
)
from src.studio.api.services.paths import episode_dir, exports_base  # noqa: E402
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
    n = len(script.rounds)
    images = [a for a in plan if a.kind == "image"]
    videos = [a for a in plan if a.kind == "video"]
    audio = [a for a in plan if a.kind == "audio"]

    # 1 réf perso + N rounds x (5 frames + 2 choix) + 1 epilogue frame.
    assert len(images) == 1 + n * 7 + 1
    # N rounds x 5 beats + 1 epilogue motion.
    assert len(videos) == n * 5 + 1
    # Narration PAR BEAT (voix conteur) : transition + N rounds x 5 + epilogue.
    assert len(audio) == 1 + n * 5 + 1
    # Garde de non-régression sur le défaut N=3 (anciens compteurs).
    assert (len(images), len(videos), len(audio)) == (23, 16, 17)


@pytest.mark.parametrize("n", [1, 2, 5])
def test_plan_scales_with_n_rounds(n):
    """Le plan d'assets suit N : composabilité du nombre de séquences-choix."""
    from src.features.scripting.fake_adventure_decomposer import (
        FakeAdventureDecomposer,
    )

    s = FakeAdventureDecomposer().decompose_adventure(
        "cave horror", "Étienne", "Marc", n_rounds=n
    )
    assert len(s.rounds) == n
    for rnd in s.rounds:  # invariant 1 fatal/round préservé par le pool
        assert sum(1 for c in rnd.choices if c.is_fatal) == 1
    plan = plan_episode_assets(s)
    assert len([a for a in plan if a.kind == "image"]) == 1 + n * 7 + 1
    assert len([a for a in plan if a.kind == "video"]) == n * 5 + 1
    assert len([a for a in plan if a.kind == "audio"]) == 1 + n * 5 + 1


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


def test_output_dir_is_configurable(monkeypatch, tmp_path):
    # Default base.
    monkeypatch.delenv("VCM_OUTPUT_DIR", raising=False)
    assert exports_base() == "exports"
    assert episode_dir("demo", 7).endswith("exports/demo/episode_7")
    # Overridable for environments where exports/ is not writable.
    out = str(tmp_path / "studio_output")
    monkeypatch.setenv("VCM_OUTPUT_DIR", out)
    assert exports_base() == out
    assert episode_dir("demo", 7) == os.path.join(out, "demo", "episode_7")


def test_fake_provider_records_calls_no_network():
    fake = FakeAssetProvider()
    url = fake.generate_image("a dark cave", "2K", "9:16")
    assert url.startswith("https://fake.local/")
    assert fake.image_calls == [("a dark cave", "2K", "9:16", None)]
    vurl = fake.animate_video("move", url, 7, "9:16", "720p")
    assert vurl.endswith(".mp4")
    assert fake.video_calls[0]["image"] == url
