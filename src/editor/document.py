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

SCHEMA_VERSION = 1


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

    track: int = 0
    start: float = 0.0
    duration: float = 0.0


class Layer(_Doc):
    """Overlay empilé dans une brique (texte / média importé / PNG / narration)."""

    type: Literal["text", "imported_media", "png_overlay", "narration"]
    z: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)


class GenerativeBrick(_Doc):
    """Brique générée par un modèle (image / vidéo / voix) — `params` libres."""

    id: str
    type: Literal["image", "video", "voice"]
    model_ref: str = ""                  # "owner/name" ou "owner/name:version"
    params: Dict[str, Any] = Field(default_factory=dict)
    context_overrides: Optional[NarrativeContext] = None
    preset_id: Optional[int] = None
    layers: List[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class MediaBrick(_Doc):
    """Média fourni par l'utilisateur (non généré) — réf asset ou chemin local."""

    id: str
    type: Literal["media"] = "media"
    asset_ref: Optional[int] = None
    source_path: Optional[str] = None
    layers: List[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class TextBrick(_Doc):
    """Texte pur posé sur la timeline (titre, carton…)."""

    id: str
    type: Literal["text"] = "text"
    payload: Dict[str, Any] = Field(default_factory=dict)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


Brick = Annotated[
    Union[GenerativeBrick, MediaBrick, TextBrick],
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
