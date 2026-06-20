"""Le pont structure → MP4 (SPEC §6, « trou #1 »).

Prouve, EN OFFLINE (FakeAssetResolver, zéro réseau), que :
  1. le resolver factice résout TOUTES les références d'un VideoSpec aventure
     (chaque asset a un fichier, chaque source de sous-titre a un transcript) ;
  2. le MoviePyRenderEngine rend les 4 types de segment en un MP4 lisible ;
  3. la chaîne complète `prompt → MP4` produit un fichier vidéo non vide.

Tout est rendu en CANVAS MINUSCULE pour rester rapide dans la boucle `make verify`.
"""

import os

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("moviepy")
pytest.importorskip("PIL")
pytest.importorskip("numpy")

# Rendu MoviePy réel → lourd : skippé par défaut (cf. conftest, --runheavy).
pytestmark = pytest.mark.render

from src.features.scripting.adventure_to_spec import adventure_to_spec  # noqa: E402
from src.features.scripting.fake_adventure_decomposer import (  # noqa: E402
    FakeAdventureDecomposer,
)
from src.videospec.models import (  # noqa: E402
    Canvas,
    CountdownSegment,
    FileAsset,
    FootageSegment,
    HeadAnchor,
    ImageAsset,
    IntroSegment,
    NameplateSpec,
    NarrationSegment,
    SubtitleTrack,
    VideoAsset,
    VideoSpec,
    VoiceAsset,
)
from src.videospec.produce import produce, produce_from_prompt  # noqa: E402
from src.videospec.render_moviepy import MoviePyRenderEngine  # noqa: E402
from src.videospec.resolve_fake import FakeAssetResolver  # noqa: E402

TINY = Canvas(width=96, height=170, fps=12)


def _adventure_spec(n_rounds: int) -> VideoSpec:
    script = FakeAdventureDecomposer().decompose_adventure("peu importe", n_rounds=n_rounds)
    spec = adventure_to_spec(script)
    return spec.model_copy(update={"canvas": TINY})


def test_fake_resolver_resolves_all_refs(tmp_path):
    """Aucune référence orpheline : tout asset a un fichier, toute voix un transcript."""
    spec = _adventure_spec(n_rounds=2)
    resolved = FakeAssetResolver().resolve(spec, str(tmp_path))

    # Chaque asset déclaré est résolu en un chemin.
    for a in spec.assets:
        assert a.id in resolved.paths, f"asset non résolu : {a.id}"
        if not isinstance(a, FileAsset):
            assert os.path.exists(resolved.paths[a.id]), f"fichier manquant : {a.id}"

    # Chaque source de sous-titres (audio) a un transcript factice.
    for seg in spec.segments:
        src = getattr(getattr(seg, "subtitles", None), "source", None)
        if src is not None:
            assert src in resolved.transcripts, f"transcript manquant : {src}"
            assert len(resolved.transcripts[src]) > 0


def test_render_minimal_spec(tmp_path):
    """Les 4 types de segment (intro/footage/narration/countdown) rendent un MP4."""
    spec = VideoSpec(
        canvas=TINY,
        assets=(
            ImageAsset(id="img", prompt="x"),
            VoiceAsset(id="narr", text="un deux trois quatre cinq"),
            VideoAsset(id="vid", prompt="x", image="img"),
            FileAsset(id="tick", path="assets/tick.wav"),
            FileAsset(id="beep", path="assets/final.wav"),
        ),
        segments=(
            IntroSegment(
                background="img",
                nameplates=(
                    NameplateSpec(text="A", placement=HeadAnchor(side="left")),
                    NameplateSpec(text="B", placement=HeadAnchor(side="right")),
                ),
            ),
            FootageSegment(video="vid", subtitles=SubtitleTrack(source="narr")),
            NarrationSegment(
                background="img", audio="narr", subtitles=SubtitleTrack(source="narr")
            ),
            CountdownSegment(background="img", tick_sound="tick", end_sound="beep"),
        ),
    )
    out = os.path.join(str(tmp_path), "out.mp4")
    produce(spec, str(tmp_path), FakeAssetResolver(), MoviePyRenderEngine(), out)

    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000

    from moviepy import VideoFileClip

    clip = VideoFileClip(out)
    try:
        assert clip.duration > 1.0
    finally:
        clip.close()


def test_prompt_to_mp4_end_to_end(tmp_path):
    """La chaîne complète prompt → MP4 (intro + 1 scène de choix + outro)."""
    out = os.path.join(str(tmp_path), "story.mp4")
    produce_from_prompt(
        prompt="une nuit dans un dirigeable abandonné",
        decomposer=FakeAdventureDecomposer(),
        resolver=FakeAssetResolver(),
        engine=MoviePyRenderEngine(),
        project_dir=str(tmp_path),
        output_path=out,
        n_rounds=1,
        canvas=TINY,
    )

    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000

    from moviepy import VideoFileClip

    clip = VideoFileClip(out)
    try:
        assert clip.duration > 2.0
    finally:
        clip.close()
