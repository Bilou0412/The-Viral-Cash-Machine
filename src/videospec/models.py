"""VideoSpec — IR déclarative de composition vidéo.

Le contrat central du studio : une vidéo est une donnée (pas du code).
Inspirations assumées :
- OpenTimelineIO : timeline = séquence de segments à durées explicites ou dérivées
- Remotion       : briques typées + props JSON (unions discriminées sur `type`)
- Terraform      : les assets sont *déclarés* ici (plan), *résolus* avant rendu (apply)

Règles de design :
- Tout est immuable (frozen) et sérialisable JSON.
- `extra="forbid"` partout : le JSON Schema dérivé contraint le structured output LLM.
- Les durées `None` sont dérivées de l'asset principal au moment du resolve
  (durée de la vidéo, durée de l'audio de narration).
- Les segments référencent les assets par id ; la cohérence des références
  est validée au niveau du VideoSpec.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Spec(BaseModel):
    """Base commune : immuable, strict."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class Canvas(_Spec):
    width: int = 1080
    height: int = 1920
    fps: int = 24


# ---------------------------------------------------------------------------
# Assets — déclarés dans le manifest, résolus avant le rendu
# ---------------------------------------------------------------------------

class VoiceAsset(_Spec):
    """Voix à synthétiser (TTS)."""

    type: Literal["voice"] = "voice"
    id: str
    text: str
    voice_id: str = "Deep_Voice_Man"


class ImageAsset(_Spec):
    """Image à générer (text-to-image)."""

    type: Literal["image"] = "image"
    id: str
    prompt: str
    size: str = "1024"
    aspect_ratio: str = "9:16"


class VideoAsset(_Spec):
    """Vidéo à générer (image-to-video). `image` et `audio` référencent des assets."""

    type: Literal["video"] = "video"
    id: str
    prompt: str
    image: str
    audio: str | None = None
    duration: float = 7.0
    resolution: str = "720x1280"
    draft: bool = False


class FileAsset(_Spec):
    """Fichier statique déjà présent sur disque (SFX, musique, fonts...)."""

    type: Literal["file"] = "file"
    id: str
    path: str


Asset = Annotated[
    VoiceAsset | ImageAsset | VideoAsset | FileAsset,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Placement & styles
# ---------------------------------------------------------------------------

class AbsolutePosition(_Spec):
    """Position normalisée (0–1) sur le canvas."""

    type: Literal["absolute"] = "absolute"
    x: float
    y: float


class HeadAnchor(_Spec):
    """Position ancrée sur une tête détectée (résolue par HeadDetector)."""

    type: Literal["head"] = "head"
    side: Literal["left", "right"]
    v_offset: int = 60


Placement = Annotated[
    AbsolutePosition | HeadAnchor,
    Field(discriminator="type"),
]


class SubtitleStyle(_Spec):
    fontsize: int = 72
    font_path: str = "assets/montserrat.bold.ttf"
    y: float = 0.78
    uppercase: bool = True


class SubtitleTrack(_Spec):
    """Sous-titres mot-à-mot dérivés d'un asset audio (transcription au resolve)."""

    source: str  # id d'un asset audio/voix à transcrire
    style: SubtitleStyle = SubtitleStyle()


class NameplateSpec(_Spec):
    text: str
    placement: Placement
    fontsize: int = 50
    color: str = "white"
    font_path: str = "assets/Minecraft.ttf"
    stroke_width: int = 3
    uppercase: bool = True


class ZoomEffect(_Spec):
    """Zoom linéaire sur la durée du segment (effet Ken Burns)."""

    scale_from: float = 1.0
    scale_to: float = 1.15


class EyeOpenTransition(_Spec):
    """Deux barres noires qui s'ouvrent verticalement."""

    duration: float = 0.8


class TimerStyle(_Spec):
    fontsize: int = 160
    size: int = 230
    font_path: str = "assets/Minecraft.ttf"


class GaugeSpec(_Spec):
    """Jauge de progression animée."""

    y: float = 0.65
    height: int = 50


# ---------------------------------------------------------------------------
# Segments — la timeline est leur séquence ordonnée
# ---------------------------------------------------------------------------

class IntroSegment(_Spec):
    """Image fixe + nameplates, révélée par une transition eye-open."""

    type: Literal["intro"] = "intro"
    background: str  # id d'un ImageAsset/FileAsset
    duration: float = 1.2
    transition: EyeOpenTransition | None = EyeOpenTransition()
    nameplates: tuple[NameplateSpec, ...] = ()


class FootageSegment(_Spec):
    """Vidéo principale (hook) avec sous-titres et nameplates incrustés."""

    type: Literal["footage"] = "footage"
    video: str  # id d'un VideoAsset/FileAsset
    duration: float | None = None  # None = durée de la vidéo
    subtitles: SubtitleTrack | None = None
    nameplates: tuple[NameplateSpec, ...] = ()


class NarrationSegment(_Spec):
    """Image de fond zoomée + voix off + sous-titres."""

    type: Literal["narration"] = "narration"
    background: str  # id d'un ImageAsset/FileAsset
    audio: str  # id d'un VoiceAsset/FileAsset — fixe la durée du segment
    duration: float | None = None  # None = durée de l'audio
    zoom: ZoomEffect | None = ZoomEffect()
    subtitles: SubtitleTrack | None = None
    nameplates: tuple[NameplateSpec, ...] = ()


class CountdownSegment(_Spec):
    """Fond flouté + compte à rebours + jauge + SFX."""

    type: Literal["countdown"] = "countdown"
    background: str  # id d'un ImageAsset/FileAsset
    blur_radius: float = 25.0
    steps: tuple[str, ...] = ("3", "2", "1")
    step_duration: float = 0.7
    timer: TimerStyle = TimerStyle()
    gauge: GaugeSpec | None = GaugeSpec()
    tick_sound: str | None = None  # id d'un FileAsset
    end_sound: str | None = None  # id d'un FileAsset
    nameplates: tuple[NameplateSpec, ...] = ()


Segment = Annotated[
    IntroSegment | FootageSegment | NarrationSegment | CountdownSegment,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# VideoSpec — racine
# ---------------------------------------------------------------------------

class VideoSpec(_Spec):
    """Description complète d'une vidéo : manifest d'assets + timeline."""

    version: Literal["1.0"] = "1.0"
    canvas: Canvas = Canvas()
    assets: tuple[Asset, ...]
    segments: tuple[Segment, ...]

    @model_validator(mode="after")
    def _check_asset_refs(self) -> "VideoSpec":
        ids = {a.id for a in self.assets}
        if len(ids) != len(self.assets):
            raise ValueError("ids d'assets dupliqués dans le manifest")

        def need(ref: str | None, where: str) -> None:
            if ref is not None and ref not in ids:
                raise ValueError(f"{where} référence l'asset inconnu '{ref}'")

        for a in self.assets:
            if isinstance(a, VideoAsset):
                need(a.image, f"VideoAsset '{a.id}'.image")
                need(a.audio, f"VideoAsset '{a.id}'.audio")

        for i, seg in enumerate(self.segments):
            where = f"segments[{i}] ({seg.type})"
            if isinstance(seg, IntroSegment):
                need(seg.background, where)
            elif isinstance(seg, FootageSegment):
                need(seg.video, where)
                if seg.subtitles:
                    need(seg.subtitles.source, f"{where}.subtitles")
            elif isinstance(seg, NarrationSegment):
                need(seg.background, where)
                need(seg.audio, where)
                if seg.subtitles:
                    need(seg.subtitles.source, f"{where}.subtitles")
            elif isinstance(seg, CountdownSegment):
                need(seg.background, where)
                need(seg.tick_sound, f"{where}.tick_sound")
                need(seg.end_sound, f"{where}.end_sound")
        return self
