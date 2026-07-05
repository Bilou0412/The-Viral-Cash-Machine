"""Construction du VideoSpec correspondant au montage historique.

Preuve de couverture : ce builder reproduit exactement la timeline codée en dur
dans RawVideoCompositor.compose() (intro eye-open → footage sous-titré →
narration zoomée → countdown 3-2-1). C'est aussi l'oracle de la future
comparaison golden entre moteurs de rendu.
"""

from .models import (
    Canvas,
    CountdownSegment,
    FileAsset,
    FootageSegment,
    HeadAnchor,
    IntroSegment,
    NameplateSpec,
    NarrationSegment,
    Segment,
    SubtitleTrack,
    VideoSpec,
)


def legacy_spec(
    char_left_name: str,
    char_right_name: str,
    with_narration: bool = True,
) -> VideoSpec:
    """Spec équivalent au montage actuel, assets pointés sur le layout exports/."""

    nameplates = (
        NameplateSpec(text=char_left_name, placement=HeadAnchor(side="left")),
        NameplateSpec(text=char_right_name, placement=HeadAnchor(side="right")),
    )

    assets: list[FileAsset] = [
        FileAsset(id="base_image", path="base_image.png"),
        FileAsset(id="main_video", path="video.mp4"),
        FileAsset(id="char_voice", path="character.mp3"),
        FileAsset(id="tick", path="assets/tick.wav"),
        FileAsset(id="beep", path="assets/final.wav"),
    ]

    segments: list[Segment] = [
        IntroSegment(background="base_image", nameplates=nameplates),
        FootageSegment(
            video="main_video",
            subtitles=SubtitleTrack(source="char_voice"),
            nameplates=nameplates,
        ),
    ]

    if with_narration:
        assets.append(FileAsset(id="narrator_voice", path="narrator.mp3"))
        segments.append(
            NarrationSegment(
                background="base_image",
                audio="narrator_voice",
                subtitles=SubtitleTrack(source="narrator_voice"),
                nameplates=nameplates,
            )
        )
        segments.append(
            CountdownSegment(
                background="base_image",
                tick_sound="tick",
                end_sound="beep",
            )
        )

    return VideoSpec(
        canvas=Canvas(),
        assets=tuple(assets),
        segments=tuple(segments),
    )
