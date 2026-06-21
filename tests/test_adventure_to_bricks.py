"""Tests de l'adaptateur PUR `adventure_to_bricks` : AdventureScript → ClipBrick.

Offline (FakeAdventureDecomposer). On vérifie surtout l'INVARIANT de couverture :
les briques génèrent exactement les mêmes assets (prompts image/motion, textes de
narration) que `adventure_to_spec` / `plan_episode_assets` — le rail « IA écrit →
je révise en briques » ne perd ni n'ajoute aucun asset génératif.
"""

import pytest

pytest.importorskip("pydantic")

from src.editor import ClipBrick, document_to_spec  # noqa: E402
from src.editor.capabilities import validate_clip  # noqa: E402
from src.features.scripting.adventure_to_bricks import (  # noqa: E402
    adventure_to_bricks,
    adventure_to_document,
)
from src.features.scripting.adventure_to_spec import adventure_to_spec  # noqa: E402
from src.features.scripting.fake_adventure_decomposer import (  # noqa: E402
    FakeAdventureDecomposer,
)
from src.features.scripting.themes import Theme  # noqa: E402
from src.studio.api.services.generation_plan import plan_episode_assets  # noqa: E402
from src.videospec.models import ImageAsset, VideoAsset, VoiceAsset  # noqa: E402


def _script(n_rounds: int):
    return FakeAdventureDecomposer().decompose_adventure(
        "cave", "Léo", "Sam", n_rounds=n_rounds
    )


def _gen_assets(spec):
    """Multisets (triés) des assets GÉNÉRATIFS d'un VideoSpec (hors FileAsset)."""
    imgs = sorted(a.prompt for a in spec.assets if isinstance(a, ImageAsset))
    vids = sorted(a.prompt for a in spec.assets if isinstance(a, VideoAsset))
    auds = sorted(a.text for a in spec.assets if isinstance(a, VoiceAsset))
    return imgs, vids, auds


@pytest.mark.parametrize("n", [1, 3])
def test_brick_node_counts_match_planned_assets(n):
    script = _script(n)
    bricks = adventure_to_bricks(script)
    planned = plan_episode_assets(script)

    n_img = sum(1 for p in planned if p.kind == "image")
    n_vid = sum(1 for p in planned if p.kind == "video")
    n_aud = sum(1 for p in planned if p.kind == "audio")

    # 1 nœud image par brique ; 1 nœud motion par brique VIDÉO ; 1 enfant
    # narration par narration planifiée.
    assert len(bricks) == n_img
    assert sum(1 for b in bricks if b.kind == "video") == n_vid
    assert sum(len(b.children) for b in bricks) == n_aud


@pytest.mark.parametrize("n", [1, 3])
def test_coverage_invariant_matches_adventure_to_spec(n):
    """Les briques compilées génèrent EXACTEMENT les mêmes assets que le spec direct."""
    script = _script(n)
    spec_from_bricks = document_to_spec(adventure_to_document(script))
    spec_direct = adventure_to_spec(script)
    assert _gen_assets(spec_from_bricks) == _gen_assets(spec_direct)


def test_all_bricks_are_ready_and_compile():
    script = _script(2)
    doc = adventure_to_document(script)
    # chaque brique est complète (prête à générer) : prompts + narration+voix.
    for brick in doc.bricks:
        assert validate_clip(brick) == {}, brick.id  # type: ignore[arg-type]
    spec = document_to_spec(doc)  # ne lève pas, refs valides
    assert len(spec.segments) == len(doc.bricks)


def test_ids_are_stable_and_unique():
    bricks = adventure_to_bricks(_script(2))
    ids = [b.id for b in bricks]
    assert len(ids) == len(set(ids))
    assert ids[0] == "ep_intro"
    assert ids[-1] == "ep_epilogue"
    assert "r0_action" in ids and "r1_survival" in ids


def test_face_cam_has_no_narration_child():
    bricks = {b.id: b for b in adventure_to_bricks(_script(1))}
    char = bricks["r0_character"]
    assert isinstance(char, ClipBrick) and char.kind == "video"
    assert char.children == []  # voix native p-video, pas de TTS séparé


def test_custom_theme_flows_into_brick_prompts():
    marker = "NEON SYNTHWAVE DA MARKER ZZZ"
    theme = Theme(
        name="custom_test", da=marker, pov="POV", pov_hands="hands",
        no_text="No text.", voice_only_audio="Audio: voice only.",
        ambient_audio="Audio: ambience.", vertical="Vertical 9:16.",
        pace_calm="calm", pace_sudden="sudden", decomposer_tone="neon",
    )
    bricks = adventure_to_bricks(_script(2), theme=theme)
    prompts = [b.image.params.get("prompt", "") for b in bricks]
    assert any(marker in p for p in prompts)
    # garde-fou : sans le thème, le marqueur est absent.
    assert not any(marker in b.image.params.get("prompt", "") for b in adventure_to_bricks(_script(2)))
