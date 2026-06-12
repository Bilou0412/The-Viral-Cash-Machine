"""Bibliothèque de prompts — méthodologie « image-first ».

Best practice vidéo IA : on NE génère JAMAIS une vidéo en texte→vidéo direct.
Pour chaque plan vidéo :
  1. `frame_*()` produit le prompt de la PREMIÈRE FRAME (image seedream) — tout
     le visuel : cadrage POV, perso, mains, décor, lumière, DA, composition.
  2. `motion_*()` produit le prompt VIDÉO (image→vidéo p-video) — UNIQUEMENT le
     mouvement (avec sa VITESSE) et ce qui est dit. Le look est déjà verrouillé
     par l'image, donc on ne re-décrit jamais le visuel ici.

Tout le format est une IMMERSION POV/FPS (le spectateur suit le protagoniste).

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

# ---------------------------------------------------------------------------
# Constantes partagées
# ---------------------------------------------------------------------------

DA = (
    "dark cinematic horror, photorealistic, heavily desaturated cold palette, "
    "deep crushed shadows, a single harsh handheld torch as the only light, "
    "wet glistening surfaces, drifting dust, fine film grain"
)
POV_HANDS = "our own bare hands visible at the lower edge of the frame"
POV = "First-person POV, immersive FPS video-game framing"
NO_TEXT = "No text, no lettering, no logos in the frame."
VOICE_ONLY_AUDIO = "Audio: voice only, no music, no ambience."
AMBIENT_AUDIO = "Audio: ambience of the place, no music."
VERTICAL = "Vertical 9:16."

# Vocabulaire de vitesse (best practice : contrôler explicitement le mouvement).
PACE_CALM = "slow, calm, unhurried, steady pace"
PACE_SUDDEN = "sudden, sharp, violent burst"


def _join(*parts: str) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


# ===========================================================================
# 1) PREMIÈRE FRAME — images riches (seedream). Tout le visuel vit ici.
# ===========================================================================

def frame_action(character_name: str, character_desc: str, environment_desc: str) -> str:
    """Première frame d'un plan d'action : on est juste derrière le perso."""
    return _join(
        f"{POV}.",
        f"We stand just behind {character_name} ({character_desc}), seen from "
        f"behind, a few steps ahead of us, about to move off through "
        f"{environment_desc}.",
        f"{POV_HANDS}.",
        DA + ".",
        "Depth, leading lines into darkness, cinematic composition.",
        NO_TEXT,
        VERTICAL,
    )


def frame_environment(character_name: str, environment_desc: str, danger_desc: str) -> str:
    """Première frame du plan d'environnement : le perso arrêté, le danger visible."""
    return _join(
        f"{POV}.",
        f"{character_name} stands still a few steps ahead of us in "
        f"{environment_desc}.",
        f"The danger dominates the frame: {danger_desc}.",
        f"{POV_HANDS}.",
        DA + ".",
        "Wide oppressive composition.",
        NO_TEXT,
        VERTICAL,
    )


def frame_character(character_name: str, character_desc: str, environment_desc: str) -> str:
    """Première frame du face-cam : le perso retourné, face à nous, proche."""
    return _join(
        f"{POV}, close shot.",
        f"{character_name} ({character_desc}) has turned to face us, very close, "
        f"locking eyes with the camera, in {environment_desc}.",
        f"Tense urgent expression, mouth starting to speak. {POV_HANDS}.",
        DA + ".",
        "Tight intimate framing.",
        NO_TEXT,
        VERTICAL,
    )


def frame_fatal(character_name: str, character_desc: str, environment_desc: str) -> str:
    """Première frame de la mort POV : la menace juste sur nous."""
    return _join(
        f"{POV}, we are the victim.",
        f"{character_name} ({character_desc}) looms right over us in "
        f"{environment_desc}, about to strike.",
        f"{POV_HANDS} raised in defense.",
        DA + ".",
        "Claustrophobic low angle, terror.",
        NO_TEXT,
        VERTICAL,
    )


def frame_survival(character_name: str, character_desc: str, environment_desc: str) -> str:
    """Première frame de la survie : le perso devant nous, le calme précaire."""
    return _join(
        f"{POV}.",
        f"{character_name} ({character_desc}) is a few steps ahead of us, having "
        f"just reached safer ground in {environment_desc}, glancing back.",
        f"{POV_HANDS}.",
        DA + ".",
        "Lingering threat in the shadows behind.",
        NO_TEXT,
        VERTICAL,
    )


def choice_image(character_name: str, option_desc: str, environment_desc: str) -> str:
    """Image d'UNE option de choix (pas de vidéo) — POV, le perso la désigne."""
    return _join(
        f"{POV}, still frame. Ahead of us in {environment_desc}: {option_desc}.",
        f"{character_name} is in frame, gesturing toward it. {POV_HANDS}.",
        "Strong central composition, readable in half a second.",
        DA + ".",
        NO_TEXT,
        VERTICAL,
    )


# ===========================================================================
# 2) MOUVEMENT — vidéos image→vidéo (p-video). Mouvement + dialogue UNIQUEMENT.
# ===========================================================================

def motion_action(character_name: str, action_motion: str) -> str:
    """Animation du plan d'action : on suit, tranquille. Le look vient de l'image."""
    return _join(
        f"Animate from the first frame. We follow {character_name} as he "
        f"{action_motion}.",
        f"{PACE_CALM}; we keep our distance and never overtake, gentle handheld "
        f"sway, no running, no sprint.",
        AMBIENT_AUDIO,
    )


def motion_environment(character_name: str) -> str:
    """Animation du plan d'environnement : presque immobile, micro-menace."""
    return _join(
        "Animate from the first frame.",
        f"Very slight first-person sway as we look at the danger; {character_name} "
        "barely shifts.",
        f"{PACE_CALM}; dust drifts, faint tremor, distant creaks.",
        AMBIENT_AUDIO,
    )


def motion_character(
    character_name: str, voice_desc: str, delivery: str, line_fr: str
) -> str:
    """Animation du face-cam : il parle. Voix native, look déjà verrouillé."""
    return _join(
        f"Animate from the first frame. {character_name} speaks straight to us in "
        f"French, {delivery}, with {voice_desc}, pressing us to choose fast, and "
        f'says exactly: "{line_fr}"',
        "Natural lip sync, intense eye contact, minimal head movement.",
        VOICE_ONLY_AUDIO,
    )


def motion_fatal(character_name: str, kill_motion: str, pov_reaction: str) -> str:
    """Animation de la mort POV : brutal."""
    return _join(
        f"Animate from the first frame. {character_name} {kill_motion}; we "
        f"{pov_reaction}.",
        f"{PACE_SUDDEN}, then stillness.",
        AMBIENT_AUDIO,
    )


def motion_survival(character_name: str, survival_motion: str) -> str:
    """Animation de la survie : on suit, méfiant."""
    return _join(
        f"Animate from the first frame. We follow {character_name} as he "
        f"{survival_motion}.",
        f"{PACE_CALM}, wary; the threat lingers behind.",
        AMBIENT_AUDIO,
    )


def narrator_audition(voice_desc: str, line_fr: str) -> str:
    """Clip jetable d'audition narrateur (texte→vidéo, visuel minimal)."""
    return _join(
        "Almost black screen: faint embers drifting in darkness.",
        f"A narrator speaks in French, off-screen, with {voice_desc}, "
        f'and says exactly: "{line_fr}"',
        VOICE_ONLY_AUDIO,
        "Static shot.",
        NO_TEXT,
        VERTICAL,
    )
