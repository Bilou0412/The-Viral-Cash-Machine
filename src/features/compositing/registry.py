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
from typing import Literal

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
