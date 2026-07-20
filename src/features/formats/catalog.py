"""Catalogue des FORMATS de vidéo — la couche « moule » au-dessus du rail.

Un FORMAT (≙ « template ») = une STRUCTURE figée (la séquence de beats/scènes) que
le décomposeur REMPLIT ; le fond (histoire, persos, dilemmes) varie à chaque vidéo,
la forme reste. C'est une **usine à moules** (« Aventure à choix », « Scènes libres »…) :
même forme, fond variable — pas un éditeur générique.

Ici on ne stocke que l'**identité** d'un format (métadonnées, import-light). Le BINDING
format→pipeline (quel décomposeur + adaptateur l'incarnent) vit au niveau service
(`studio/api/services/formats.py`), car il compose des services (clé OpenAI…).

Décision actée : la structure d'un format est **codée en dur** (le décomposeur+adaptateur
qui l'incarnent). On n'extrait un schéma de slots générique qu'au **3ᵉ** format (règle de
trois), pas depuis n=1. Aujourd'hui : #1 `aventure` (CYOA), #2 `scenes` (3 niveaux).
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownFormatError(ValueError):
    """Format absent du catalogue."""


@dataclass(frozen=True)
class VideoFormat:
    """L'IDENTITÉ d'un format (la forme). Le fond est rempli par le décomposeur."""

    id: str            # aligné sur `Episode.format` ("aventure", "scenes")
    label: str         # nom lisible
    tagline: str       # accroche courte (une phrase)
    description: str   # ce que le moule IMPOSE (forme) vs ce que l'IA REMPLIT (fond)


# Ordre = ordre d'affichage. #1 aventure (déjà codé en dur), #2 scènes libres.
_FORMATS: tuple[VideoFormat, ...] = (
    VideoFormat(
        id="aventure",
        label="Aventure à choix",
        tagline="CYOA : 2 personnages, des dilemmes à choix, une issue fatale par manche.",
        description=(
            "FORME FIGÉE : intro des 2 persos → N manches (action → décor → face-cam → "
            "2 choix dont 1 fatal → issue) → épilogue. FOND VARIABLE : le thème, les "
            "personnages, les dilemmes et les répliques, remplis par le décomposeur."
        ),
    ),
    VideoFormat(
        id="scenes",
        label="Scènes libres",
        tagline="Une suite de scènes (décor + plans courts) qui racontent une idée.",
        description=(
            "FORME : Vidéo → Scènes → Plans (photo d'établissement + plans i2v courts). "
            "FOND VARIABLE : l'arc, les scènes, les décors et les plans, remplis par le "
            "décomposeur 3 niveaux."
        ),
    ),
    VideoFormat(
        id="systeme",
        label="Système expliqué",
        tagline="Une image d'un système → on explique comment il marche, en plans de 5 s.",
        description=(
            "FORME : image d'un système (bâtiment, composant, foule, chantier…) → N étapes "
            "expliquées, chacune un plan court (≤ 5 s) avec narration FR + visuel EN. "
            "FOND VARIABLE : le système identifié et le déroulé, remplis par le décomposeur "
            "à VISION (Fake offline / OpenAI)."
        ),
    ),
)

_BY_ID = {f.id: f for f in _FORMATS}

DEFAULT_FORMAT = "aventure"   # = défaut de la colonne `Episode.format`


def list_formats() -> list[VideoFormat]:
    """Le catalogue, dans l'ordre d'affichage."""
    return list(_FORMATS)


def get_format(format_id: str) -> VideoFormat:
    """Le format d'`id` donné (lève `UnknownFormatError` si absent)."""
    try:
        return _BY_ID[format_id]
    except KeyError as e:
        raise UnknownFormatError(
            f"format inconnu '{format_id}' ; connus : {sorted(_BY_ID)}"
        ) from e
