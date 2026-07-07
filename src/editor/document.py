"""EditorDocument — format d'AUTORING de l'éditeur timeline (E1).

Différent de `VideoSpec` (contrat de RENDU : frozen, strict, golden). Ici le front
**mute** le document : `params` libres par brique (validés contre le schéma du modèle
ailleurs, pas par pydantic), calques empilés, et un **contexte récit global hérité +
surcharges locales** par brique. Sérialisable JSON, versionné (`schema_version`).

Import-light : pydantic + `videospec.Canvas` uniquement (aucune dépendance lourde) —
le package `editor` doit s'importer sans openai/replicate (collecte pytest).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..videospec.models import Canvas

SCHEMA_VERSION = 4


class _Doc(BaseModel):
    """Base authoring : strict mais NON frozen (le front édite en place)."""

    model_config = ConfigDict(extra="forbid")


class NarrativeContext(_Doc):
    """Le « récit » qui devient le contexte des prompts d'assets."""

    text: str = ""                       # la trame / l'histoire
    characters: dict[str, str] = Field(default_factory=dict)  # nom -> description
    art_direction: str = ""              # DA (se mappe sur Theme.da)
    extra: dict[str, str] = Field(default_factory=dict)       # libre K/V


class TimelinePlacement(_Doc):
    """Position d'une brique sur la timeline (secondes)."""

    track: Annotated[int, Field(ge=0)] = 0
    start: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0
    duration: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0


class Layer(_Doc):
    """Overlay empilé dans une brique (texte / média importé / PNG / narration)."""

    type: Literal["text", "imported_media", "png_overlay", "narration"]
    z: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)


class GenNode(_Doc):
    """Un nœud de génération = les **arguments d'UN appel API** (image ou vidéo).

    `model_ref` désigne le modèle (registry / "owner/name[:version]") et `params`
    porte ses arguments bruts (prompt, taille, durée…), NON contraints par pydantic
    — validés ailleurs contre le schéma du modèle (contrat de capacité, étape B2).
    """

    model_ref: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


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
    params: dict[str, Any] = Field(default_factory=dict)


class GenerativeBrick(_Doc):
    """Brique générée par un modèle (image / vidéo / voix) — `params` libres.

    LEGACY (schema v1, à plat) : conservée valide pour ne pas casser
    `resolve.py` / `editor_generation.py`. Le nouveau format composite est
    `ClipBrick` ; le repli v1→clip viendra avec B1 (réécâblage des consommateurs).
    """

    id: Annotated[str, Field(min_length=1)]
    type: Literal["image", "video", "voice"]
    model_ref: str = ""                  # "owner/name" ou "owner/name:version"
    params: dict[str, Any] = Field(default_factory=dict)
    context_overrides: NarrativeContext | None = None
    preset_id: int | None = None
    layers: list[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class MediaBrick(_Doc):
    """Média fourni par l'utilisateur (non généré) — réf asset ou chemin local."""

    id: Annotated[str, Field(min_length=1)]
    type: Literal["media"] = "media"
    asset_ref: int | None = None
    source_path: str | None = None
    layers: list[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class TextBrick(_Doc):
    """Texte pur posé sur la timeline (titre, carton…)."""

    id: Annotated[str, Field(min_length=1)]
    type: Literal["text"] = "text"
    payload: dict[str, Any] = Field(default_factory=dict)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)


class CharacterEntry(_Doc):
    """Fiche d'un personnage dans la BIBLE — l'identité RÉCURRENTE (v4).

    Ce que fixe le casting/costume d'une prod : apparence physique, tenue par
    défaut, voix, traits. Les plans la RÉFÉRENCENT (par `id`) et surchargent
    localement. C'est le support des « trous » d'un futur template de série.
    """

    id: Annotated[str, Field(min_length=1)]
    name: str = ""
    appearance: str = ""   # physique récurrent (EN, prompt visuel)
    wardrobe: str = ""     # tenue par défaut (EN)
    voice_id: str = ""     # profil vocal (banque VoiceProfile)
    traits: str = ""       # caractère / attitude


class ShotCharacter(_Doc):
    """Un personnage PRÉSENT dans un plan : référence bible + surcharges locales."""

    ref: str = ""          # id d'une CharacterEntry ("" = perso ad hoc, hors bible)
    name: str = ""         # nom d'affichage / si hors bible
    wardrobe: str = ""     # surcharge de tenue pour CE plan
    expression: str = ""   # expression / émotion dans le plan
    action: str = ""       # ce que fait le personnage dans le plan


class ShotBrief(_Doc):
    """Les CHAMPS MÉTIER d'un plan visuel (v4), regroupés par le compilateur.

    Remplace le prompt-blob : chaque département a son champ (déco, lumière,
    cadrage, personnages). `compile_shot.compile_shot_prompt` les réunit en LE
    prompt EN envoyé au modèle. `shot=None` sur une brique → chemin blob legacy.
    """

    decor: str = ""        # lieu, moment, ambiance, accessoires (EN)
    lumiere: str = ""      # lumière (EN)
    cadrage: str = ""      # taille de plan + angle (EN)
    characters: list[ShotCharacter] = Field(default_factory=list)
    extra: str = ""        # complément libre (EN)


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
    motion: GenNode | None = None                  # kind=video uniquement
    zoom: ZoomSpec | None = None                   # kind=photo uniquement (Ken Burns)
    shot: ShotBrief | None = None                  # v4 : champs métier (sinon blob legacy)
    children: list[AudioChild] = Field(default_factory=list)
    context_overrides: NarrativeContext | None = None
    preset_id: int | None = None
    layers: list[Layer] = Field(default_factory=list)
    placement: TimelinePlacement = Field(default_factory=TimelinePlacement)

    @model_validator(mode="after")
    def _check_kind(self) -> ClipBrick:
        if self.kind == "photo" and self.motion is not None:
            raise ValueError("une brique PHOTO ne peut pas porter de 'motion' (image→video)")
        if self.kind == "video" and self.zoom is not None:
            raise ValueError("'zoom' (Ken Burns) est réservé aux briques PHOTO")
        child_ids = [c.id for c in self.children]
        if len(child_ids) != len(set(child_ids)):
            raise ValueError("ids d'enfants dupliqués dans la brique")
        return self


Brick = Annotated[
    ClipBrick | GenerativeBrick | MediaBrick | TextBrick,
    Field(discriminator="type"),
]


class Track(_Doc):
    """Une piste horizontale de la timeline."""

    index: int = 0
    role: Literal["video", "audio", "overlay"] = "video"


class Scene(_Doc):
    """Regroupement narratif de briques (v3) — un INDEX, pas une imbrication.

    Une scène = un contexte concentré : la photo d'environnement (contexte figé)
    + les plans (shots) qui l'animent. Elle **référence** des briques du document
    par id (les briques restent une liste plate → le rendu/`document_to_spec`
    reste inchangé). Lenient : une brique peut n'appartenir à aucune scène.
    """

    id: Annotated[str, Field(min_length=1)]
    title: str = ""
    context: NarrativeContext = Field(default_factory=NarrativeContext)
    environment_photo_ref: str = ""              # id de la brique PHOTO figée
    shot_ids: list[str] = Field(default_factory=list)  # refs ordonnées vers bricks


class EditorDocument(_Doc):
    """Document d'autoring complet : canvas + contexte global + pistes + briques."""

    schema_version: int = SCHEMA_VERSION
    title: str = "Sans titre"
    canvas: Canvas = Field(default_factory=Canvas)
    global_context: NarrativeContext = Field(default_factory=NarrativeContext)
    tracks: list[Track] = Field(default_factory=list)
    bricks: list[Brick] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    bible: list[CharacterEntry] = Field(default_factory=list)  # v4 : personnages récurrents

    @model_validator(mode="after")
    def _check(self) -> EditorDocument:
        ids = [b.id for b in self.bricks]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de briques dupliqués dans le document")
        bible_ids = [c.id for c in self.bible]
        if len(bible_ids) != len(set(bible_ids)):
            raise ValueError("ids de personnages dupliqués dans la bible")
        known = set(ids)
        for b in self.bricks:
            for layer in getattr(b, "layers", []):
                if layer.type == "narration":
                    ref = layer.payload.get("brick_ref")
                    if ref is not None and ref not in known:
                        raise ValueError(
                            f"calque narration référence une brique inconnue '{ref}'"
                        )
        scene_ids = [s.id for s in self.scenes]
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("ids de scènes dupliqués dans le document")
        for scene in self.scenes:
            refs = [*scene.shot_ids]
            if scene.environment_photo_ref:
                refs.append(scene.environment_photo_ref)
            for ref in refs:
                if ref not in known:
                    raise ValueError(
                        f"scène '{scene.id}' référence une brique inconnue '{ref}'"
                    )
        return self
