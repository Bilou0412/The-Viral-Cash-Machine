"""RenderModel — contrat de RENDU résolu (lu par Remotion).

Pipeline : `EditorDocument` (authoring) --resolve()--> `RenderModel` (frozen, assets
résolus en URLs fichier) --> composition Remotion (`<Player>` pour l'aperçu, `renderMedia`
pour l'export MP4).

C'est le **contrat unique Python ↔ Node** : ce module (pydantic) et
`render/src/renderModel.ts` (zod) doivent rester en lockstep — un test de contrat dumpe
un `RenderModel` Python et le valide contre le schéma zod côté Node.

Frozen + strict comme `VideoSpec` (c'est un contrat de rendu, pas de l'authoring).
"""

from typing import Any, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..videospec.models import Canvas


class _R(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SubtitleWord(_R):
    """Un mot sous-titré avec son timing (résolu via Whisper au resolve)."""

    text: str
    start: float
    end: float


class RenderClip(_R):
    """Un élément résolu posé sur une piste, prêt pour Remotion."""

    id: str
    media: Literal["video", "image", "audio", "text", "overlay"]
    src: Optional[str] = None          # URL fichier (API) ; None pour un clip texte
    start: float                        # secondes sur la timeline
    duration: float                     # secondes
    track: int = 0
    z: int = 0                          # ordre d'empilement (overlays)
    text: Optional[str] = None          # contenu d'un clip texte
    style: Optional[Dict[str, Any]] = None      # police/couleur/position (libre)
    subtitles: Tuple[SubtitleWord, ...] = ()
    transform: Optional[Dict[str, Any]] = None  # position/scale/opacity (libre)


class RenderModel(_R):
    """Vidéo résolue : canvas + clips ordonnés + durée totale. Props Remotion."""

    version: Literal["1.0"] = "1.0"
    canvas: Canvas = Field(default_factory=Canvas)
    clips: Tuple[RenderClip, ...] = ()
    total_duration: float = 0.0
