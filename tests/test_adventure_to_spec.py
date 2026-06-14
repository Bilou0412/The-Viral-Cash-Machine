"""Tests de l'adaptateur PUR `adventure_to_spec` : AdventureScript → VideoSpec.

Pur pytest, aucun réseau : le script vient du FakeAdventureDecomposer (offline,
déterministe). On vérifie : ordre des segments (INTRO → N blocs → OUTRO),
intégrité référentielle des assets (construction de VideoSpec ne lève pas),
mise à l'échelle avec N, et propagation d'un thème non-défaut dans les prompts.
"""

import pytest

pytest.importorskip("pydantic")

from src.features.scripting.adventure_to_spec import adventure_to_spec  # noqa: E402
from src.features.scripting.fake_adventure_decomposer import (  # noqa: E402
    FakeAdventureDecomposer,
)
from src.features.scripting.themes import Theme  # noqa: E402
from src.videospec.models import (  # noqa: E402
    ImageAsset,
    VideoSpec,
    VideoAsset,
)

# Nombre de segments par bloc séquence-choix, dans l'ordre rendu par le
# compositor : action(footage+narration), environment(footage+narration),
# face-cam(footage), écran de choix(narration), countdown,
# fatal(narration), survival(narration) = 9.
_SEG_PER_ROUND = 9


def _script(n_rounds: int):
    return FakeAdventureDecomposer().decompose_adventure(
        "cave", "Léo", "Sam", n_rounds=n_rounds
    )


def test_spec_validates_and_orders_intro_first_outro_last():
    spec = adventure_to_spec(_script(3))
    assert isinstance(spec, VideoSpec)

    # INTRO en tête, OUTRO (narration de l'épilogue) en queue.
    assert spec.segments[0].type == "intro"
    assert spec.segments[-1].type == "narration"

    # 1 intro + N*_SEG_PER_ROUND + 1 outro.
    n = 3
    assert len(spec.segments) == 1 + n * _SEG_PER_ROUND + 1

    # Aucun segment "intro" en dehors du premier ; un seul intro au total.
    assert sum(1 for s in spec.segments if s.type == "intro") == 1


def test_reference_integrity_holds():
    # VideoSpec valide ses refs à la construction : si adventure_to_spec produit
    # un ref pendant, la construction aurait levé. On revalide explicitement via
    # un round-trip JSON pour couvrir le validateur sans ambiguïté.
    spec = adventure_to_spec(_script(3))
    restored = VideoSpec.model_validate_json(spec.model_dump_json())
    assert restored == spec

    ids = {a.id for a in spec.assets}
    # Échantillon : tout VideoAsset référence une image déclarée.
    for a in spec.assets:
        if isinstance(a, VideoAsset):
            assert a.image in ids


@pytest.mark.parametrize("n", [1, 3, 5])
def test_segment_count_scales_with_n(n):
    spec = adventure_to_spec(_script(n))
    assert len(spec.segments) == 1 + n * _SEG_PER_ROUND + 1
    # Un seul intro, et exactement un countdown par round.
    assert sum(1 for s in spec.segments if s.type == "intro") == 1
    assert sum(1 for s in spec.segments if s.type == "countdown") == n


def test_custom_theme_flows_into_image_prompts():
    marker = "NEON SYNTHWAVE DA MARKER ZZZ"
    theme = Theme(
        name="custom_test",
        da=marker,
        pov="POV",
        pov_hands="hands",
        no_text="No text.",
        voice_only_audio="Audio: voice only.",
        ambient_audio="Audio: ambience.",
        vertical="Vertical 9:16.",
        pace_calm="calm",
        pace_sudden="sudden",
        decomposer_tone="neon",
    )
    spec = adventure_to_spec(_script(2), theme=theme)

    # La DA du thème (theme.da) est injectée verbatim dans les prompts d'images
    # de plan (frames) — donc présente dans au moins un ImageAsset.
    image_prompts = [a.prompt for a in spec.assets if isinstance(a, ImageAsset)]
    assert any(marker in p for p in image_prompts)

    # Garde-fou : le thème par défaut ne contient PAS ce marqueur.
    default_spec = adventure_to_spec(_script(2))
    default_image_prompts = [
        a.prompt for a in default_spec.assets if isinstance(a, ImageAsset)
    ]
    assert not any(marker in p for p in default_image_prompts)
