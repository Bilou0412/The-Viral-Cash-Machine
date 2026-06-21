"""EditorDocument — format d'AUTORING de l'éditeur timeline (E1).

Différent de `VideoSpec` (contrat de RENDU : frozen, strict, golden). Ici le front
**mute** le document : `params` libres par brique (validés contre le schéma du modèle
ailleurs, pas par pydantic), calques empilés, et un **contexte récit global hérité +
surcharges locales** par brique. Sérialisable JSON, versionné (`schema_version`).

Import-light : pydantic + `videospec.Canvas` uniquement (aucune dépendance lourde) —
le package `editor` doit s'importer sans openai/replicate (collecte pytest).
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..videospec.models import Canvas

SCHEMA_VERSION = 2


class _Doc(BaseModel):
    """Base authoring : strict mais NON frozen (le front édite en place)."""

    model_config = ConfigDict(extra="forbid")


class NarrativeContext(_Doc):
    """Le « récit » qui devient le contexte des prompts d'assets."""

    text: str = ""                       # la trame / l'histoire
    characters: Dict[str, str] = Field(default_factory=dict)  # nom -> description
    art_direction: str = ""              # DA (se mappe sur Theme.da)
    extra: Dict[str, str] = Field(default_factory=dict)       # libre K/V


class TimelinePlacement(_Doc):
    """Position d'une brique sur la timeline (secondes)."""

    track: Annotated[int, Field(ge=0)] = 0
    start: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0
    duration: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0


class Layer(_Doc):
    """Overlay empilé dans une brique (texte / média importé / PNG / narration)."""

    type: Literal["text", "imported_media", "png_overlay", "narration"]
    z: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)


class GenNode(_Doc):
    """Un nœud de génération = les **arguments d'UN appel API** (image ou vidéo).

    `model_ref` désigne le modèle (registry / "owner/name[:version]") et `params`
    porte ses arguments bruts (prompt, taille, durée…), NON contraints par pydantic
    — validés ailleurs contre le schéma du modèle (contrat de capacité, étape B2).
    """

    model_ref: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class ZoomSpec(_Doc):
    """Effet Ken Burns d'une brique PHOTO : agencement de rendu, PAS un appel API."""

    from_scale: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.0
    to_scale: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.2
    focus_x: Annotated[float, Field(ge=0, le=1)] = 0.5
    focus_y: Annotated[float, Field(ge=0, le=1)] = 0.5


class AudioChild(_Doc):
    """Enfant audio d'une brique (narration off / dialogue perso) = un appel TTS."""

    id: Annotated[str, Field(min_length=1)]
    role: Literal["narration", "dialogue"]
    model_ref: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class GenerativeBrick(_Doc):
    """Brique générée par un modèle (image / vidéo / voix) — `params` libres.

    LEGACY (schema v1, à plat) : conservée valide pour ne pas casser
    `resolve.py` / `editor_generation.py`. Le nouveau format composite est
    `ClipBrick` ; le repli v1→clip viendra avec B1 (réécâblage des consommateurs).
    """

    id: Annotated[str, Field(min_length=1)]
    type: Literal["image", "video", "voice"]
    model_ref: str = ""                  # "owner/name" ou "owner/name:version"
    params: Dict[str, Any] = Field(default_factory=dict)
    context_overrides: Optional[NarrativeContext] = None
    preset_id: Optional[int] = None
    layers: List[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class MediaBrick(_Doc):
    """Média fourni par l'utilisateur (non généré) — réf asset ou chemin local."""

    id: Annotated[str, Field(min_length=1)]
    type: Literal["media"] = "media"
    asset_ref: Optional[int] = None
    source_path: Optional[str] = None
    layers: List[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class TextBrick(_Doc):
    """Texte pur posé sur la timeline (titre, carton…)."""

    id: Annotated[str, Field(min_length=1)]
    type: Literal["text"] = "text"
    payload: Dict[str, Any] = Field(default_factory=dict)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class ClipBrick(_Doc):
    """Brique média composite posée sur la timeline : VIDÉO ou PHOTO.

    Porte les deux rôles d'une brique :
    1. **les arguments des appels API** qui la génèrent — `image` (text→image : la
       photo, ou la first-frame d'une vidéo), `motion` (image→video, vidéo seule),
       enfants audio (narration / dialogue) ;
    2. **l'agencement** — `placement` (piste, début, durée) + l'imbrication
       parent/enfants.

    Se compile vers un `Segment` de `VideoSpec` à l'étape B1 (PHOTO+zoom →
    `NarrationSegment`, VIDÉO → `FootageSegment`, etc.).
    """

    id: Annotated[str, Field(min_length=1)]
    type: Literal["clip"] = "clip"
    kind: Literal["video", "photo"]
    image: GenNode = Field(default_factory=GenNode)   # toujours présent
    motion: Optional[GenNode] = None                  # kind=video uniquement
    zoom: Optional[ZoomSpec] = None                   # kind=photo uniquement (Ken Burns)
    children: List[AudioChild] = Field(default_factory=list)
    context_overrides: Optional[NarrativeContext] = None
    preset_id: Optional[int] = None
    layers: List[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)

    @model_validator(mode="after")
    def _check_kind(self) -> "ClipBrick":
        if self.kind == "photo" and self.motion is not None:
            raise ValueError("une brique PHOTO ne peut pas porter de 'motion' (image→video)")
        if self.kind == "video" and self.zoom is not None:
            raise ValueError("'zoom' (Ken Burns) est réservé aux briques PHOTO")
        child_ids = [c.id for c in self.children]
        if len(child_ids) != len(set(child_ids)):
            raise ValueError("ids d'enfants dupliqués dans la brique")
        return self


Brick = Annotated[
    Union[ClipBrick, GenerativeBrick, MediaBrick, TextBrick],
    Field(discriminator="type"),
]


class Track(_Doc):
    """Une piste horizontale de la timeline."""

    index: int = 0
    role: Literal["video", "audio", "overlay"] = "video"


class EditorDocument(_Doc):
    """Document d'autoring complet : canvas + contexte global + pistes + briques."""

    schema_version: int = SCHEMA_VERSION
    title: str = "Sans titre"
    canvas: Canvas = Field(default_factory=Canvas)
    global_context: NarrativeContext = Field(default_factory=NarrativeContext)
    tracks: List[Track] = Field(default_factory=list)
    bricks: List[Brick] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "EditorDocument":
        ids = [b.id for b in self.bricks]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de briques dupliqués dans le document")
        known = set(ids)
        for b in self.bricks:
            for layer in getattr(b, "layers", []):
                if layer.type == "narration":
                    ref = layer.payload.get("brick_ref")
                    if ref is not None and ref not in known:
                        raise ValueError(
                            f"calque narration référence une brique inconnue '{ref}'"
                        )
        return self
