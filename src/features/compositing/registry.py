"""Registre de briques (palette) — métadonnées déclaratives des primitives.

Ce module est une *palette* : il nomme, de façon stable, les briques de
génération et de montage qui existent déjà dans le projet, sans rien changer à
leur fonctionnement. L'intérêt : un bloc de composition peut déclarer quelles
briques il utilise (``uses: tuple[str, ...]``) en se référant à ces noms
stables, SANS modifier la manière dont le compositeur invoque les primitives.

C'est purement du métadonnée :

- Aucune primitive n'est importée ici. Le champ ``Brick.ref`` est une *chaîne*
  pointée (dotted reference) vers l'implémentation réelle, précisément pour
  garder ce module léger à l'import et exempt de dépendances lourdes
  (moviepy / replicate / openai / pydantic). Il se charge donc dans
  l'environnement de test sans rien tirer.

Les vraies primitives vivent ailleurs :

- Générateurs d'assets : ``features.assets.ports.AssetProvider``
  (``generate_image`` / ``animate_video`` / ``synthesize_voice``).
- Montage : ``features.compositing.adventure_compositor`` (timer, choix, zoom
  Ken Burns, face-cam, narration calée en vitesse) et
  ``features.compositing.overlays`` (overlays sous-titres / timer / plaque de
  nom / jauge). La détection des têtes pour la plaque de nom vit dans
  ``features.compositing.heads``.
- Effets modélisés en IR déclarative : ``videospec.models`` (p.ex.
  ``EyeOpenTransition``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

BrickKind = Literal["image", "video", "voice", "montage"]


@dataclass(frozen=True)
class Brick:
    """Une brique réutilisable, décrite par métadonnées (pas d'import).

    Attributes:
        name: Nom stable de la brique (clé dans ``REGISTRY``).
        kind: Catégorie — ``"image"``, ``"video"``, ``"voice"`` ou ``"montage"``.
        summary: Résumé en une ligne de ce que fait la brique.
        ref: Référence pointée (chaîne) vers l'implémentation réelle, p.ex.
            ``"features.assets.ports.AssetProvider.generate_image"``. C'est
            volontairement une chaîne et non un import, pour garder ce module
            léger et sans dépendances lourdes.
    """

    name: str
    kind: BrickKind
    summary: str
    ref: str


REGISTRY: dict[str, Brick] = {
    # --- Générateurs (features.assets.ports.AssetProvider) -----------------
    "image.seedream": Brick(
        name="image.seedream",
        kind="image",
        summary="Génère une image (text/image-to-image) à partir d'un prompt.",
        ref="features.assets.ports.AssetProvider.generate_image",
    ),
    "video.pvideo": Brick(
        name="video.pvideo",
        kind="video",
        summary="Anime une image en vidéo (image-to-video) à partir d'un prompt.",
        ref="features.assets.ports.AssetProvider.animate_video",
    ),
    "voice.minimax": Brick(
        name="voice.minimax",
        kind="voice",
        summary="Synthétise une voix (TTS) à partir d'un texte et d'un voice_id.",
        ref="features.assets.ports.AssetProvider.synthesize_voice",
    ),
    # --- Primitives de montage (adventure_compositor + overlays) ----------
    "montage.timer": Brick(
        name="montage.timer",
        kind="montage",
        summary="Écran compte à rebours 3-2-1 sur fond flouté + jauge + ticks/beep.",
        ref="features.compositing.adventure_compositor._timer_screen",
    ),
    "montage.choice": Brick(
        name="montage.choice",
        kind="montage",
        summary="Écran des choix : 2 photos en succession, bascule sur le mot « ou ».",
        ref="features.compositing.adventure_compositor._choice_screen",
    ),
    "montage.subtitles": Brick(
        name="montage.subtitles",
        kind="montage",
        summary="Sous-titres mot-à-mot (Whisper) incrustés via SubtitleOverlay.",
        ref="features.compositing.overlays.SubtitleOverlay",
    ),
    "montage.nameplate": Brick(
        name="montage.nameplate",
        kind="montage",
        summary="Plaque de nom du perso suivi, positionnée via la détection de têtes.",
        ref="features.compositing.overlays.NameplateOverlay",
    ),
    "montage.zoom": Brick(
        name="montage.zoom",
        kind="montage",
        summary="Zoom Ken Burns sur une image fixe sur la durée du segment.",
        ref="features.compositing.adventure_compositor._ken_burns",
    ),
    "montage.facecam": Brick(
        name="montage.facecam",
        kind="montage",
        summary="Face-cam : voix native conservée + sous-titres de cette voix.",
        ref="features.compositing.adventure_compositor._facecam_video",
    ),
    "montage.narrate": Brick(
        name="montage.narrate",
        kind="montage",
        summary="Cale narration et visuel à la même durée par la vitesse (audio+vidéo).",
        ref="features.compositing.adventure_compositor._narrate_over",
    ),
    # --- Effets modélisés en VideoSpec (videospec.models) -----------------
    "montage.eye_open": Brick(
        name="montage.eye_open",
        kind="montage",
        summary="Transition eye-open : deux barres noires qui s'ouvrent verticalement.",
        ref="videospec.models.EyeOpenTransition",
    ),
}


def get_brick(name: str) -> Brick:
    """Renvoie la brique nommée.

    Raises:
        KeyError: si ``name`` n'est pas une brique connue ; le message liste
            les noms valides.
    """
    try:
        return REGISTRY[name]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(
            f"brique inconnue : {name!r}. Briques disponibles : {known}"
        ) from None


def bricks_by_kind(kind: str) -> list[Brick]:
    """Renvoie toutes les briques d'une catégorie donnée (ordre du registre)."""
    return [b for b in REGISTRY.values() if b.kind == kind]


# ---------------------------------------------------------------------------
# E2 — Contrats de capacité + modèles préférés
# ---------------------------------------------------------------------------
#
# Pour chaque *kind* de brique génératrice (image / video / voice), on déclare :
#
#   1. un CONTRAT DE CAPACITÉ : les champs d'entrée que la brique attend. Sert à
#      deux choses : (a) valider les params d'une brique avant exécution
#      (`validate_params`) ; (b) filtrer une recherche de modèles libres en ne
#      retenant que ceux qui exposent les entrées requises (`model_satisfies`).
#
#   2. trois MODÈLES PRÉFÉRÉS Replicate, dans l'ordre : low-cost,
#      quality-price, premium. Le slot quality-price reste, quand c'est sensé,
#      le modèle déjà utilisé par le projet.
#
# Les `aliases` couvrent le fait qu'un même concept porte des noms différents
# d'un modèle Replicate à l'autre (p.ex. l'image source d'un i2v peut s'appeler
# `image`, `image_input`, `first_frame`, `start_image` ou `init_image`). Un
# champ est « satisfait » dès que son `name` OU l'un de ses alias est présent.


@dataclass(frozen=True)
class CapabilityField:
    """Un champ d'entrée d'un contrat de capacité.

    Attributes:
        name: Nom canonique du champ (celui qu'on utilise côté projet).
        required: True si la brique ne peut pas s'exécuter sans ce champ.
        aliases: Noms alternatifs qu'un modèle peut exposer et qui satisfont
            ce même champ (p.ex. ``image`` ↔ ``init_image``).
    """

    name: str
    required: bool
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityContract:
    """Le contrat d'un kind : ses champs d'entrée + 3 modèles préférés.

    Attributes:
        kind: ``"image"``, ``"video"`` ou ``"voice"``.
        fields: Champs d'entrée attendus (requis et optionnels).
        preferred_models: Exactement 3 réfs Replicate, dans l'ordre
            low-cost, quality-price, premium.
    """

    kind: str
    fields: tuple[CapabilityField, ...]
    preferred_models: tuple[str, ...]


CONTRACTS: dict[str, CapabilityContract] = {
    "image": CapabilityContract(
        kind="image",
        fields=(
            CapabilityField("prompt", required=True),
            CapabilityField(
                "image_input",
                required=False,
                aliases=("image", "reference", "init_image"),
            ),
            CapabilityField(
                "aspect_ratio",
                required=False,
                aliases=("size", "ratio"),
            ),
        ),
        # low-cost / quality-price / premium — vérifiés via Replicate MCP
        # (toutes ces réfs existent et exposent les entrées REQUISES) :
        #   black-forest-labs/flux-schnell — required: prompt ; +aspect_ratio
        #   bytedance/seedream-4.5 (projet) — required: prompt ; +image_input,
        #       aspect_ratio (size)
        #   google/imagen-4-ultra — required: prompt ; +aspect_ratio
        preferred_models=(
            "black-forest-labs/flux-schnell",
            "bytedance/seedream-4.5",
            "google/imagen-4-ultra",
        ),
    ),
    "video": CapabilityContract(
        kind="video",
        fields=(
            CapabilityField("prompt", required=True),
            CapabilityField(
                "duration",
                required=True,
                aliases=("length", "num_frames"),
            ),
            CapabilityField(
                "image",
                required=True,
                aliases=(
                    "image_input",
                    "first_frame",
                    "start_image",
                    "init_image",
                ),
            ),
            CapabilityField(
                "audio",
                required=False,
                aliases=("audio_input", "with_audio", "sound"),
            ),
            CapabilityField(
                "motion",
                required=False,
                aliases=("motion_prompt", "camera_motion"),
            ),
        ),
        # low-cost / quality-price / premium — vérifiés via Replicate MCP
        # (chacun expose les entrées REQUISES prompt + duration|num_frames +
        # image|start_image) :
        #   wan-video/wan-2.2-i2v-fast — required: prompt, image ;
        #       +num_frames (duration)
        #   prunaai/p-video (projet) — required: prompt ; +duration, image,
        #       audio
        #   kwaivgi/kling-v2.5-turbo-pro — required: prompt ;
        #       +duration, image, start_image
        preferred_models=(
            "wan-video/wan-2.2-i2v-fast",
            "prunaai/p-video",
            "kwaivgi/kling-v2.5-turbo-pro",
        ),
    ),
    "voice": CapabilityContract(
        kind="voice",
        fields=(
            CapabilityField(
                "text",
                required=True,
                aliases=("prompt", "input_text"),
            ),
            CapabilityField(
                "voice_id",
                required=True,
                aliases=("voice", "speaker", "voice_name"),
            ),
        ),
        # low-cost / quality-price / premium — vérifiés via Replicate MCP
        # (chacun expose les entrées REQUISES text + voice_id) :
        #   minimax/speech-02-turbo — required: text ; +voice_id
        #   minimax/speech-2.8-turbo (projet) — required: text ; +voice_id
        #   minimax/speech-2.8-hd — required: text ; +voice_id
        preferred_models=(
            "minimax/speech-02-turbo",
            "minimax/speech-2.8-turbo",
            "minimax/speech-2.8-hd",
        ),
    ),
}


def _field_keys(f: CapabilityField) -> tuple[str, ...]:
    """Noms qui satisfont un champ : son nom canonique + ses alias."""
    return (f.name, *f.aliases)


def validate_params(kind: str, params: dict[str, object]) -> list[str]:
    """Renvoie la liste des champs REQUIS manquants (vide = valide).

    Un champ est satisfait si son ``name`` OU l'un de ses alias est une clé
    présente et non ``None`` dans ``params``.

    Raises:
        KeyError: si ``kind`` n'a pas de contrat.
    """
    contract = get_contract(kind)
    present = {k for k, v in params.items() if v is not None}
    missing: list[str] = []
    for fld in contract.fields:
        if not fld.required:
            continue
        if not present.intersection(_field_keys(fld)):
            missing.append(fld.name)
    return missing


def model_satisfies(
    contract: CapabilityContract, input_schema_properties: "Iterable[str]"
) -> bool:
    """True ssi chaque champ REQUIS (nom ou alias) figure dans les propriétés.

    ``input_schema_properties`` = les clés des propriétés d'entrée du schéma
    OpenAPI d'un modèle Replicate. On ne contrôle que les champs requis : les
    optionnels n'écartent jamais un modèle.
    """
    props = set(input_schema_properties)
    for fld in contract.fields:
        if not fld.required:
            continue
        if not props.intersection(_field_keys(fld)):
            return False
    return True


def get_contract(kind: str) -> CapabilityContract:
    """Renvoie le contrat de capacité du ``kind`` donné.

    Raises:
        KeyError: si ``kind`` est inconnu ; le message liste les kinds valides.
    """
    try:
        return CONTRACTS[kind]
    except KeyError:
        known = ", ".join(sorted(CONTRACTS))
        raise KeyError(
            f"kind sans contrat : {kind!r}. Kinds disponibles : {known}"
        ) from None
