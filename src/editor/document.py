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

SCHEMA_VERSION = 5


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


# -- Architecture 3 niveaux (v5) : Vidéo → Scène → Plan -----------------------
# Sous-modèles PARTAGÉS par les niveaux (str défaut "" ; listes défaut []).
# Le compilateur fusionne PLAN > SCÈNE > VIDÉO (cf. `compile_shot`).


class Lumiere(_Doc):
    """Un état d'éclairage (base décor, ambiance scène, ou override plan)."""

    sources: str = ""
    direction: str = ""
    qualite: str = ""       # douce / dure
    temperature: str = ""   # chaude / froide / K
    contraste: str = ""


class Cadre(_Doc):
    """Le cadrage d'une prise (niveau PLAN)."""

    taille_plan: str = ""   # très large … très gros plan
    focale: str = ""        # 24mm … 85mm+
    angle_hauteur: str = ""  # hauteur d'œil / plongée / contre-plongée
    mise_au_point: str = ""  # fixe / rack focus


class Profondeur(_Doc):
    """Les 3 plans de profondeur, tels que cadrés (niveau PLAN)."""

    avant_plan: str = ""
    plan_moyen: str = ""
    arriere_plan: str = ""


class Camera(_Doc):
    """Le mouvement caméra d'une prise (niveau PLAN)."""

    type: str = ""          # fixe / pano / travelling / orbite / zoom…
    vitesse: str = ""
    depart_arrivee: str = ""  # d'où part le cadre → où il finit


class CharacterEntry(_Doc):
    """Fiche d'un personnage dans la BIBLE (niveau VIDÉO) — identité RÉCURRENTE.

    Définie UNE fois ; les plans la RÉFÉRENCENT (par `id`) et ne décrivent que
    l'ACTION (jamais l'apparence). Support des « trous » d'un template de série.
    """

    id: Annotated[str, Field(min_length=1)]
    name: str = ""
    appearance: str = ""   # physique récurrent (EN, prompt visuel)
    wardrobe: str = ""     # tenue par défaut (EN)
    voice_id: str = ""     # profil vocal (banque VoiceProfile)
    traits: str = ""       # caractère / attitude


class LocationEntry(_Doc):
    """Fiche d'un DÉCOR dans la BIBLE (niveau VIDÉO) — le lieu défini UNE fois.

    Une Scène ne CONTIENT pas un décor : elle le RÉFÉRENCE (`location_ref`) et le
    fait varier (moment, météo…). Réutilisable d'une scène à l'autre → cohérence.
    """

    ref: Annotated[str, Field(min_length=1)]
    lieu: str = ""
    echelle: str = ""       # exigu / vaste
    int_ext: str = ""       # int / ext
    layout_spatial: str = ""  # ce qui est où (indépendant du cadrage)
    palette: str = ""
    matieres: str = ""
    props_fixes: list[str] = Field(default_factory=list)
    lumiere_base: Lumiere = Field(default_factory=Lumiere)


class PersonnagePresent(_Doc):
    """Un personnage PRÉSENT dans un plan : `ref` bible + son ACTION (jamais l'apparence)."""

    ref: str = ""          # id d'une CharacterEntry ("" = ad hoc)
    action: str = ""
    trajectoire: str = ""
    vitesse: str = ""
    expression: str = ""
    etat_debut: str = ""   # interpolation i2v : état initial…
    etat_fin: str = ""     # …→ état final


class ElementSecondaire(_Doc):
    """Un élément animé secondaire (cheveux, enseigne, drapeau…)."""

    quoi: str = ""
    mouvement: str = ""
    etat_debut: str = ""
    etat_fin: str = ""


class Physique(_Doc):
    """Un phénomène physique/environnemental animé (vent, eau, feu, neige…)."""

    element: str = ""
    comportement: str = ""
    intensite_direction: str = ""


class LumiereTemps(_Doc):
    """Un changement d'éclairage DANS la prise (ombre qui bouge, néon, jour→nuit)."""

    ce_qui_change: str = ""
    depart_arrivee: str = ""


class Son(_Doc):
    """Le son propre à la prise (niveau PLAN). `ambiance_override` "" = hérite du room tone scène."""

    dialogue_voix: str = ""
    bruitage_sfx: str = ""       # synchro aux actions du plan
    perspective_mixage: str = ""
    dynamique_silence: str = ""
    ambiance_override: str = ""
    transition_audio: str = ""


class Segment(_Doc):
    """Un beat de la mini-timeline interne d'une prise."""

    debut_s: float = 0.0
    fin_s: float = 0.0
    image_camera: str = ""
    action_sujet: str = ""
    son: str = ""


class Continuite(_Doc):
    """Liaisons ACTIVES avec les plans voisins (l'arbre garantit le reste)."""

    lien_precedent: str = ""
    lien_suivant: str = ""


class IntentionGlobale(_Doc):
    """L'intention au niveau VIDÉO."""

    genre: str = ""
    ton: str = ""
    arc_narratif: str = ""


class RenderMeta(_Doc):
    """Le « contenant » (niveau VIDÉO) — format/rendu, hérité par tout."""

    ratio: str = "9:16"
    fps: int = 24
    resolution: str = ""
    style_rendu: str = ""
    grain_etalonnage: str = ""
    epoque_defaut: str = ""


class ShotBrief(_Doc):
    """Le PLAN (v5) : tout ce qui est PROPRE à la prise i2v — jamais hérité.

    Le décor, la lumière ambiante et le room tone viennent de la Scène (résolus au
    build par `compile_shot`). Ici : la frame de départ, le cadre, la caméra,
    l'action des persos présents (par `ref`), la physique, le son synchro, le rythme.
    `shot=None` sur une brique → chemin blob legacy inchangé.
    """

    start_image: str = ""   # note de composition de la frame de départ
    sujet: str = ""         # sujet LIBRE EN quand le plan n'est pas « perso-dans-décor »
    #                         (illustration d'un choix, plan symbolique, produit…). Sinon "".
    cadre: Cadre = Field(default_factory=Cadre)
    profondeur: Profondeur = Field(default_factory=Profondeur)
    camera: Camera = Field(default_factory=Camera)
    personnages_presents: list[PersonnagePresent] = Field(default_factory=list)
    elements_secondaires: list[ElementSecondaire] = Field(default_factory=list)
    physique_environnement: list[Physique] = Field(default_factory=list)
    lumiere_override: Lumiere | None = None  # None = hérite de la scène
    lumiere_temps: LumiereTemps = Field(default_factory=LumiereTemps)
    son: Son = Field(default_factory=Son)
    timeline: list[Segment] = Field(default_factory=list)
    intention_plan: str = ""
    continuite: Continuite = Field(default_factory=Continuite)


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
    # v5 — la scène RÉFÉRENCE un décor (bible) et le fait VARIER. Ces champs sont
    # HÉRITÉS par tous ses plans (le plan peut surcharger la lumière / le room tone).
    location_ref: str = ""                       # → EditorDocument.location_bible
    epoque_override: str = ""                     # "" = hérite de meta.epoque_defaut
    saison: str = ""
    moment_jour: str = ""
    meteo: str = ""
    lumiere_ambiante: Lumiere = Field(default_factory=Lumiere)
    mood: str = ""
    ambiance_sonore: str = ""                     # room tone continu (hérité)
    musique_override: str = ""                    # "" = hérite de musique_score
    intention_scene: str = ""


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
    # v5 — niveau VIDÉO : le contenant + l'intention + les bibles réutilisables.
    meta: RenderMeta = Field(default_factory=RenderMeta)
    intention_globale: IntentionGlobale = Field(default_factory=IntentionGlobale)
    musique_score: str = ""
    location_bible: list[LocationEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> EditorDocument:
        ids = [b.id for b in self.bricks]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de briques dupliqués dans le document")
        bible_ids = [c.id for c in self.bible]
        if len(bible_ids) != len(set(bible_ids)):
            raise ValueError("ids de personnages dupliqués dans la bible")
        loc_ids = [locn.ref for locn in self.location_bible]
        if len(loc_ids) != len(set(loc_ids)):
            raise ValueError("refs de décors dupliqués dans la location_bible")
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
