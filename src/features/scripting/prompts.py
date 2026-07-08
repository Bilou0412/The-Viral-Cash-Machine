"""Bibliothèque de prompts — méthodologie « image-first ».

Best practice vidéo IA : on NE génère JAMAIS une vidéo en texte→vidéo direct.
Pour chaque plan vidéo :
  1. `frame_*()` produit le prompt de la PREMIÈRE FRAME (image seedream) — tout
     le visuel : cadrage POV, perso, mains, décor, lumière, DA, composition.
  2. `motion_*()` produit le prompt VIDÉO (image→vidéo p-video) — UNIQUEMENT le
     mouvement (avec sa VITESSE) et ce qui est dit. Le look est déjà verrouillé
     par l'image, donc on ne re-décrit jamais le visuel ici.

Tout le format est une IMMERSION POV/FPS (le spectateur suit le protagoniste).

DA / thème : chaque builder accepte un `theme` optionnel (cf. `themes.py`). Par
défaut (`theme=None`) il utilise le thème « horror », et les fragments produits
sont IDENTIQUES à l'ancien comportement (les constantes de module DA/POV/… sont
dérivées de ce thème) — garde golden. Passer un autre `Theme` change la DA.

RÈGLES D'OR :
1. Une ligne = une contrainte. Court et dense.
2. Dialogue exact entre guillemets, manière de dire AVANT la réplique.
3. Voix réinjectée VERBATIM entre les clips d'un même perso (cohérence vocale).
4. Ne jamais nommer ce qu'on ne veut pas voir.
5. Jamais de texte demandé à l'image (overlays au montage).
6. POV/FPS : mains visibles, protagoniste toujours dans le cadre.
7. Visuels EN, dialogues FR.
8. La VITESSE du mouvement est explicite (calme par défaut) — corrige la dérive.
"""


from .themes import Theme, get_theme

# ---------------------------------------------------------------------------
# Constantes partagées — DÉRIVÉES du thème par défaut (« horror »).
# Conservées pour la compat (imports existants `from .prompts import DA`, tests).
# ---------------------------------------------------------------------------

_DEFAULT_THEME = get_theme("horror")


def _theme(theme: Theme | None) -> Theme:
    """Le thème effectif (fallback : « horror »)."""
    return theme if theme is not None else _DEFAULT_THEME


DA = _DEFAULT_THEME.da
POV_HANDS = _DEFAULT_THEME.pov_hands
POV = _DEFAULT_THEME.pov
NO_TEXT = _DEFAULT_THEME.no_text
VOICE_ONLY_AUDIO = _DEFAULT_THEME.voice_only_audio
AMBIENT_AUDIO = _DEFAULT_THEME.ambient_audio
VERTICAL = _DEFAULT_THEME.vertical

# Vocabulaire de vitesse (best practice : contrôler explicitement le mouvement).
PACE_CALM = _DEFAULT_THEME.pace_calm
PACE_SUDDEN = _DEFAULT_THEME.pace_sudden


def _join(*parts: str) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def _solo(character_name: str) -> str:
    """Scène déserte : seul le compagnon est là (anti « gens en plus » à l'image)."""
    return (
        f"Deserted, empty place: only {character_name} is here with us — "
        "no other people, no crowd, no bystanders, no extra figures."
    )


# ===========================================================================
# 1) PREMIÈRE FRAME — images riches (seedream). Tout le visuel vit ici.
# ===========================================================================

def frame_action(
    character_name: str,
    character_desc: str,
    environment_desc: str,
    theme: Theme | None = None,
) -> str:
    """Première frame d'un plan d'action : on est juste derrière le perso."""
    t = _theme(theme)
    return _join(
        f"{t.pov}.",
        f"We stand just behind {character_name} ({character_desc}), seen from "
        f"behind, a few steps ahead of us, about to move off through "
        f"{environment_desc}.",
        f"{t.pov_hands}.",
        t.da + ".",
        "Depth, leading lines into darkness, cinematic composition.",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


def frame_environment(
    character_name: str,
    environment_desc: str,
    danger_desc: str,
    theme: Theme | None = None,
) -> str:
    """Première frame du plan d'environnement : le perso arrêté, le danger visible."""
    t = _theme(theme)
    return _join(
        f"{t.pov}.",
        f"{character_name} stands still a few steps ahead of us in "
        f"{environment_desc}.",
        f"The danger dominates the frame: {danger_desc}.",
        f"{t.pov_hands}.",
        t.da + ".",
        "Wide oppressive composition.",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


def frame_character(
    character_name: str,
    character_desc: str,
    environment_desc: str,
    theme: Theme | None = None,
) -> str:
    """Première frame du face-cam : le perso retourné, face à nous, proche."""
    t = _theme(theme)
    return _join(
        f"{t.pov}, close shot.",
        f"{character_name} ({character_desc}) has turned to face us, very close, "
        f"locking eyes with the camera, in {environment_desc}.",
        f"Tense urgent expression, mouth starting to speak. {t.pov_hands}.",
        t.da + ".",
        "Tight intimate framing.",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


def frame_fatal(
    character_name: str,
    character_desc: str,
    environment_desc: str,
    theme: Theme | None = None,
) -> str:
    """Première frame de la mort POV : la menace juste sur nous."""
    t = _theme(theme)
    return _join(
        f"{t.pov}, we are the victim.",
        f"{character_name} ({character_desc}) turns ON us, now the aggressor, "
        f"looming right over us in {environment_desc}, deliberately about to strike.",
        f"{t.pov_hands} raised in defense.",
        t.da + ".",
        "Claustrophobic low angle, terror.",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


def frame_survival(
    character_name: str,
    character_desc: str,
    environment_desc: str,
    theme: Theme | None = None,
) -> str:
    """Première frame de la survie : le perso devant nous, le calme précaire."""
    t = _theme(theme)
    return _join(
        f"{t.pov}.",
        f"{character_name} ({character_desc}) is a few steps ahead of us, having "
        f"just reached safer ground in {environment_desc}, glancing back.",
        f"{t.pov_hands}.",
        t.da + ".",
        "Lingering threat in the shadows behind.",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


def choice_image(
    character_name: str,
    option_desc: str,
    environment_desc: str,
    theme: Theme | None = None,
) -> str:
    """Image d'UNE option de choix (pas de vidéo) — POV, le perso la désigne."""
    t = _theme(theme)
    return _join(
        f"{t.pov}, still frame. Ahead of us in {environment_desc}: {option_desc}.",
        f"{character_name} is in frame, gesturing toward it. {t.pov_hands}.",
        "Strong central composition, readable in half a second.",
        t.da + ".",
        _solo(character_name),
        t.no_text,
        t.vertical,
    )


# ===========================================================================
# 2) MOUVEMENT — vidéos image→vidéo (p-video). Mouvement + dialogue UNIQUEMENT.
# ===========================================================================

def motion_action(
    character_name: str, action_motion: str, theme: Theme | None = None
) -> str:
    """Animation du plan d'action : on suit, tranquille. Le look vient de l'image."""
    t = _theme(theme)
    return _join(
        f"Animate from the first frame. We follow {character_name} as he "
        f"{action_motion}.",
        f"{t.pace_calm}; we keep our distance and never overtake, gentle handheld "
        f"sway, no running, no sprint.",
        t.ambient_audio,
    )


def motion_environment(
    character_name: str, theme: Theme | None = None
) -> str:
    """Animation du plan d'environnement : presque immobile, micro-menace."""
    t = _theme(theme)
    return _join(
        "Animate from the first frame.",
        f"Very slight first-person sway as we look at the danger; {character_name} "
        "barely shifts.",
        f"{t.pace_calm}; dust drifts, faint tremor, distant creaks.",
        t.ambient_audio,
    )


def motion_character(
    character_name: str,
    voice_desc: str,
    delivery: str,
    line_fr: str,
    theme: Theme | None = None,
) -> str:
    """Animation du face-cam : il parle. Voix native, look déjà verrouillé."""
    t = _theme(theme)
    return _join(
        f"Animate from the first frame. {character_name} speaks straight to us in "
        f"French, {delivery}, with {voice_desc}, pressing us to choose fast, and "
        f'says exactly: "{line_fr}"',
        "Natural lip sync, intense eye contact, minimal head movement.",
        t.voice_only_audio,
    )


def motion_fatal(
    character_name: str,
    kill_motion: str,
    pov_reaction: str,
    theme: Theme | None = None,
) -> str:
    """Animation de la mort POV : brutal."""
    t = _theme(theme)
    return _join(
        f"Animate from the first frame. {character_name} {kill_motion}; we "
        f"{pov_reaction}.",
        f"{t.pace_sudden}, then stillness.",
        t.ambient_audio,
    )


def motion_survival(
    character_name: str, survival_motion: str, theme: Theme | None = None
) -> str:
    """Animation de la survie : on suit, méfiant."""
    t = _theme(theme)
    return _join(
        f"Animate from the first frame. We follow {character_name} as he "
        f"{survival_motion}.",
        f"{t.pace_calm}, wary; the threat lingers behind.",
        t.ambient_audio,
    )


