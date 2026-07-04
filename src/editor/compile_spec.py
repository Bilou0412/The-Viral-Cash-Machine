"""compile_spec() — `EditorDocument` (briques composites) → `VideoSpec` (B1).

Adaptateur PUR, à sens unique, hors-ligne (aucune I/O / réseau / DB) — testable
sur l'hôte. Il ne traite que les **`ClipBrick`** (le format composite de B0) :

- chaque clip dérive ses **assets** (`ImageAsset` pour la photo / first-frame,
  `VideoAsset` pour le motion, `VoiceAsset` pour l'enfant audio) ;
- et son **segment** dans la timeline :
    * `kind="video"`            → `FootageSegment` (vidéo + sous-titres) ;
    * `kind="photo"` + audio    → `NarrationSegment` (image zoomée + voix off) ;
    * `kind="photo"` sans audio → `IntroSegment` (image fixe).

Les briques LEGACY plates (`GenerativeBrick`/`MediaBrick`/`TextBrick`) ne font PAS
partie du chemin VideoSpec : elles restent servies par `resolve.py` (preview Node)
et seront repliées en clips ultérieurement. Elles sont donc **ignorées** ici.

Limites B1 (explicites, levées en cas d'usage) :
- au plus **un** enfant audio par clip (multi-voix déféré) ;
- une PHOTO **zoomée sans narration** n'est pas représentable (`NarrationSegment`
  exige un audio, `IntroSegment` n'a pas de zoom) → `ValueError`.
"""

from __future__ import annotations

from typing import Any

from ..videospec.models import (
    Asset,
    FootageSegment,
    ImageAsset,
    IntroSegment,
    NarrationSegment,
    Segment,
    SubtitleTrack,
    VideoAsset,
    VideoSpec,
    VoiceAsset,
    ZoomEffect,
)
from ._fields import field_value
from .document import AudioChild, ClipBrick, EditorDocument, GenNode

_DEFAULT_VIDEO_DURATION = 7.0


def _prompt(node: GenNode, kind: str) -> str:
    """Prompt d'un nœud (alias-conscient via le contrat ``kind``, vide par défaut)."""
    value = field_value(node.params, kind, "prompt")
    return value if isinstance(value, str) else ""


def _single_audio_child(clip: ClipBrick) -> AudioChild | None:
    """L'unique enfant audio du clip, ou None. Lève si le clip en a plusieurs."""
    if len(clip.children) > 1:
        raise ValueError(
            f"clip '{clip.id}' : B1 ne supporte qu'un seul enfant audio "
            f"(multi-voix déféré), {len(clip.children)} trouvés"
        )
    return clip.children[0] if clip.children else None


def _voice_asset(clip: ClipBrick, child: AudioChild) -> VoiceAsset:
    params = child.params
    text = field_value(params, "voice", "text")
    voice_id = field_value(params, "voice", "voice_id")
    kwargs: dict[str, Any] = {"id": f"{clip.id}__voice", "text": text or ""}
    if isinstance(voice_id, str) and voice_id:
        kwargs["voice_id"] = voice_id
    return VoiceAsset(**kwargs)


def _image_asset(clip: ClipBrick) -> ImageAsset:
    params = clip.image.params
    kwargs: dict[str, Any] = {"id": f"{clip.id}__img", "prompt": _prompt(clip.image, "image")}
    for key in ("size", "aspect_ratio"):
        val = params.get(key)
        if isinstance(val, str) and val:
            kwargs[key] = val
    return ImageAsset(**kwargs)


def _video_asset(clip: ClipBrick, image_id: str, audio_id: str | None) -> VideoAsset:
    motion = clip.motion or GenNode()
    params = motion.params
    duration = field_value(params, "video", "duration")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        duration = clip.placement.duration if clip.placement.duration > 0 else _DEFAULT_VIDEO_DURATION
    kwargs: dict[str, Any] = {
        "id": f"{clip.id}__vid",
        "prompt": _prompt(motion, "video") or _prompt(clip.image, "image"),
        "image": image_id,
        "duration": float(duration),
    }
    if audio_id is not None:
        kwargs["audio"] = audio_id
    if isinstance(params.get("resolution"), str):
        kwargs["resolution"] = params["resolution"]
    if bool(params.get("draft")):
        kwargs["draft"] = True
    return VideoAsset(**kwargs)


def _zoom(clip: ClipBrick) -> ZoomEffect:
    z = clip.zoom
    if z is None:
        return ZoomEffect()
    return ZoomEffect(scale_from=z.from_scale, scale_to=z.to_scale)


def _compile_clip(clip: ClipBrick) -> tuple[list[Asset], Segment]:
    """Un clip → (ses assets, son segment)."""
    assets: list[Asset] = []

    image = _image_asset(clip)
    assets.append(image)

    child = _single_audio_child(clip)
    voice_id: str | None = None
    if child is not None:
        voice = _voice_asset(clip, child)
        assets.append(voice)
        voice_id = voice.id

    if clip.kind == "video":
        video = _video_asset(clip, image.id, voice_id)
        assets.append(video)
        subtitles = SubtitleTrack(source=voice_id) if voice_id else None
        return assets, FootageSegment(video=video.id, subtitles=subtitles)

    # kind == "photo"
    if voice_id is not None:
        return assets, NarrationSegment(
            background=image.id,
            audio=voice_id,
            zoom=_zoom(clip),
            subtitles=SubtitleTrack(source=voice_id),
        )

    if clip.zoom is not None:
        raise ValueError(
            f"clip '{clip.id}' : une PHOTO zoomée a besoin d'une narration "
            f"(NarrationSegment exige un audio) — ajoute un enfant audio ou retire le zoom"
        )

    duration = clip.placement.duration if clip.placement.duration > 0 else None
    kwargs: dict[str, Any] = {"background": image.id, "transition": None}
    if duration is not None:
        kwargs["duration"] = duration
    return assets, IntroSegment(**kwargs)


def document_to_spec(doc: EditorDocument) -> VideoSpec:
    """Dérive un `VideoSpec` depuis les `ClipBrick` d'un `EditorDocument`.

    Les clips sont ordonnés par `(placement.start, placement.track)`. Les briques
    non-composites (legacy) sont ignorées. Le `canvas` du document est réutilisé tel
    quel (c'est déjà un `videospec.Canvas`). L'intégrité référentielle des assets est
    vérifiée par le validateur de `VideoSpec`.
    """
    clips = sorted(
        (b for b in doc.bricks if isinstance(b, ClipBrick)),
        key=lambda c: (c.placement.start, c.placement.track),
    )

    assets: list[Asset] = []
    segments: list[Segment] = []
    for clip in clips:
        clip_assets, segment = _compile_clip(clip)
        assets.extend(clip_assets)
        segments.append(segment)

    return VideoSpec(canvas=doc.canvas, assets=tuple(assets), segments=tuple(segments))
