"""Thème (Direction Artistique) — la DA en donnée, appliquée en cascade.

Un `Theme` regroupe les fragments de DA jusqu'ici codés en dur dans `prompts.py`
(style visuel, POV, rythme, audio) + un `decomposer_tone` (ton injecté au script).
Le thème par défaut « horror » reproduit VERBATIM l'ancien comportement, donc les
constantes de `prompts.py` (et les golden tests) restent inchangées.

Cascade de résolution d'un fragment (le plus spécifique gagne) :

    override ASSET  ▸  override BLOC  ▸  défaut du THÈME

via `resolve(asset_override, block_override, theme_value)`.

Module import-light (stdlib uniquement) qui NE dépend PAS de `prompts.py` :
c'est `prompts.py` qui dérive ses constantes d'ici (évite l'import circulaire).
"""

from dataclasses import dataclass
from typing import Dict, Optional, TypeVar


@dataclass(frozen=True)
class Theme:
    """Direction artistique d'une vidéo : fragments réinjectés dans les prompts."""

    name: str
    da: str                 # style visuel global (réinjecté dans chaque image)
    pov: str                # cadrage caméra
    pov_hands: str          # mains visibles (immersion POV)
    no_text: str            # interdiction de texte à l'image
    voice_only_audio: str   # consigne audio (voix seule)
    ambient_audio: str      # consigne audio (ambiance)
    vertical: str           # format 9:16
    pace_calm: str          # vocabulaire de vitesse — calme
    pace_sudden: str        # vocabulaire de vitesse — brutal
    decomposer_tone: str    # ton injecté au script (prompt système du décomposeur)
    label: str = ""         # libellé affichable (UI) ; défaut → name


# Thème par défaut — valeurs LIFTÉES VERBATIM de prompts.py (garde golden).
HORROR = Theme(
    name="horror",
    da=(
        "dark cinematic horror, photorealistic, heavily desaturated cold palette, "
        "deep crushed shadows, a single harsh handheld torch as the only light, "
        "wet glistening surfaces, drifting dust, fine film grain"
    ),
    pov="First-person POV, immersive FPS video-game framing",
    pov_hands="our own bare hands visible at the lower edge of the frame",
    no_text="No text, no lettering, no logos in the frame.",
    voice_only_audio="Audio: voice only, no music, no ambience.",
    ambient_audio="Audio: ambience of the place, no music.",
    vertical="Vertical 9:16.",
    pace_calm="slow, calm, unhurried, steady pace",
    pace_sudden="sudden, sharp, violent burst",
    decomposer_tone="dark cinematic horror",
    label="Horreur",
)

DEFAULT_THEME_NAME = "horror"

THEMES: Dict[str, Theme] = {HORROR.name: HORROR}


def get_theme(name: str = DEFAULT_THEME_NAME) -> Theme:
    """Retourne le thème enregistré sous `name` (défaut : « horror »)."""
    try:
        return THEMES[name]
    except KeyError:
        raise KeyError(f"thème inconnu : {name!r} (connus : {sorted(THEMES)})")


def register_theme(theme: Theme) -> None:
    """Enregistre (ou remplace) un thème dans le registre."""
    THEMES[theme.name] = theme


def list_themes() -> list[dict[str, str]]:
    """Liste des thèmes pour l'UI : [{name, label}, ...] (label → name si vide)."""
    return [
        {"name": t.name, "label": t.label or t.name}
        for t in THEMES.values()
    ]


T = TypeVar("T")


def resolve(
    asset_override: Optional[T], block_override: Optional[T], theme_value: T
) -> T:
    """Cascade de DA : asset ▸ bloc ▸ thème (premier non-None gagne)."""
    if asset_override is not None:
        return asset_override
    if block_override is not None:
        return block_override
    return theme_value
