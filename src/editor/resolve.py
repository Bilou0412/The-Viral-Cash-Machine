"""resolve() — `EditorDocument` (authoring) → `RenderModel` (contrat de rendu).

PUR et hors-ligne (aucune I/O, aucun réseau) — donc testable sur l'hôte. La
résolution des assets (génération + téléchargement) est faite AILLEURS
(`editor_generation`) ; ici on reçoit déjà une table ``asset_src`` qui mappe
**brick id → URL fichier** (servie par l'API) pour les briques dont l'asset est
prêt. `resolve` se contente d'aplatir le document en clips ordonnés.

Mapping (1 brique → 1 clip principal + 1 clip par calque empilé) :

- Brique générative ``image`` → clip média ``"image"`` ; ``video`` → ``"video"`` ;
  ``voice`` → ``"audio"`` (src = ``asset_src[brick.id]``).
- Brique média → ``"video"`` ou ``"image"`` selon l'extension de
  ``source_path``/du src résolu.
- Brique texte → clip ``"text"`` (``text=payload["content"]``, ``style=payload``).
- Chaque ``Layer`` devient un clip supplémentaire à un ``z`` plus élevé :
  text/png_overlay → ``"overlay"``/``"text"`` ; imported_media →
  ``"image"``/``"video"`` ; narration → ``"audio"`` référençant l'asset de la
  brique ``payload["brick_ref"]`` via ``asset_src``.

Les sous-titres ne sont PAS transcrits ici (resterait offline) — ``subtitles=()``
(TODO : Whisper au moment du rendu/preview).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .document import (
    EditorDocument,
    GenerativeBrick,
    Layer,
    MediaBrick,
    TextBrick,
)
from .render_model import RenderClip, RenderModel

# Extensions vidéo connues (tout le reste = image pour un média).
_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi")
_AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")


def _media_kind_from_path(path: Optional[str]) -> str:
    """Devine "video"/"image"/"audio" depuis l'extension (défaut: image)."""
    if not path:
        return "image"
    low = path.lower().split("?", 1)[0]
    if low.endswith(_VIDEO_EXTS):
        return "video"
    if low.endswith(_AUDIO_EXTS):
        return "audio"
    return "image"


def _layer_clip(
    brick_id: str,
    layer: Layer,
    layer_index: int,
    start: float,
    duration: float,
    track: int,
    asset_src: Dict[str, str],
) -> Optional[RenderClip]:
    """Construit le clip d'un calque empilé (z plus élevé que la brique)."""
    z = max(layer.z, layer_index + 1)
    payload = dict(layer.payload)
    clip_id = f"{brick_id}:layer{layer_index}"

    if layer.type == "text":
        return RenderClip(
            id=clip_id,
            media="text",
            start=start,
            duration=duration,
            track=track,
            z=z,
            text=payload.get("content") or payload.get("text"),
            style=payload,
        )
    if layer.type == "png_overlay":
        return RenderClip(
            id=clip_id,
            media="overlay",
            src=payload.get("src") or payload.get("source_path"),
            start=start,
            duration=duration,
            track=track,
            z=z,
            style=payload,
        )
    if layer.type == "imported_media":
        src = payload.get("src") or payload.get("source_path")
        return RenderClip(
            id=clip_id,
            media=_media_kind_from_path(src),  # type: ignore[arg-type]
            src=src,
            start=start,
            duration=duration,
            track=track,
            z=z,
            style=payload,
        )
    if layer.type == "narration":
        ref = payload.get("brick_ref")
        src = asset_src.get(ref) if ref else None
        return RenderClip(
            id=clip_id,
            media="audio",
            src=src,
            start=start,
            duration=duration,
            track=track,
            z=z,
        )
    return None


def resolve(doc: EditorDocument, asset_src: Dict[str, str]) -> RenderModel:
    """Aplatit un ``EditorDocument`` en ``RenderModel`` (frozen, prêt Remotion).

    Args:
        doc: le document d'autoring.
        asset_src: brick id → URL fichier (pour les briques génératives/média
            dont l'asset est prêt). Une brique absente de la table donne un clip
            sans ``src`` (le rendu côté Node gère le placeholder).

    Returns:
        Un ``RenderModel`` dont ``clips`` contient, dans l'ordre des briques, le
        clip principal de chaque brique suivi de ses clips de calques.
    """
    clips: List[RenderClip] = []
    max_end = 0.0

    for brick in doc.bricks:
        placement = brick.placement
        start = placement.start
        duration = placement.duration
        track = placement.track
        max_end = max(max_end, start + duration)

        main: Optional[RenderClip] = None

        if isinstance(brick, GenerativeBrick):
            src = asset_src.get(brick.id)
            media = {
                "image": "image",
                "video": "video",
                "voice": "audio",
            }[brick.type]
            main = RenderClip(
                id=brick.id,
                media=media,  # type: ignore[arg-type]
                src=src,
                start=start,
                duration=duration,
                track=track,
                z=0,
            )
        elif isinstance(brick, MediaBrick):
            src = asset_src.get(brick.id) or brick.source_path
            media = _media_kind_from_path(src or brick.source_path)
            main = RenderClip(
                id=brick.id,
                media=media,  # type: ignore[arg-type]
                src=src,
                start=start,
                duration=duration,
                track=track,
                z=0,
            )
        elif isinstance(brick, TextBrick):
            payload: Dict[str, Any] = dict(brick.payload)
            main = RenderClip(
                id=brick.id,
                media="text",
                start=start,
                duration=duration,
                track=track,
                z=0,
                text=payload.get("content") or payload.get("text"),
                style=payload,
            )

        if main is not None:
            clips.append(main)

        # Calques empilés (les briques texte n'en ont pas dans le modèle).
        for layer_index, layer in enumerate(getattr(brick, "layers", [])):
            layer_clip = _layer_clip(
                brick.id, layer, layer_index, start, duration, track, asset_src
            )
            if layer_clip is not None:
                clips.append(layer_clip)

    return RenderModel(
        canvas=doc.canvas,
        clips=tuple(clips),
        total_duration=max_end,
    )
