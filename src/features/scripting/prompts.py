"""Bibliothèque de prompts — le composant n°1 du système.

Chaque type d'asset a son template à slots. Les templates assemblent des blocs
réutilisables. RÈGLES D'OR (apprises en tests réels, cf. EXTENSION_PLAN.md) :

1. Une ligne = une contrainte fonctionnelle. Court et dense, jamais dilué.
2. Dialogue exact entre guillemets, manière de dire AVANT la réplique.
   Répliques courtes (moins de paraphrase).
3. Description de voix réinjectée VERBATIM — jamais reformulée entre deux
   clips d'une même identité. C'est le mécanisme de cohérence vocale.
4. Ne JAMAIS mentionner ce qu'on ne veut pas voir (nommer = faire apparaître).
5. Jamais de texte demandé à l'image — le texte réel vient des overlays.
6. Caméra statique : bloc anti-dérive, toujours présent sur les clips.
7. Visuels en ANGLAIS, dialogues en FRANÇAIS.

Toute modification d'un template doit passer par ce module (versionné, testé
par tests/test_prompts.py). Pas de prompt en dur ailleurs dans le code.
"""

# ---------------------------------------------------------------------------
# Blocs réutilisables
# ---------------------------------------------------------------------------

STATIC_CAMERA = (
    "Static locked-off camera. No camera movement, no zoom, no pan, "
    "no background change."
)

NO_TEXT = "No text, no lettering, no logos anywhere in the frame."

VERTICAL = "Vertical 9:16 format."

HORROR_STYLE = (
    "Dark cinematic horror atmosphere, realistic, oppressive shadows, "
    "desaturated cold palette, single hard light source, fine film grain."
)

VOICE_ONLY_AUDIO = (
    "Audio: voice only. No background music, no ambient sound, no echo."
)

AMBIENT_AUDIO = "Audio: natural ambient sound of the scene, no music."


def _join(*parts: str) -> str:
    """Assemble les blocs non vides en un prompt compact."""
    return " ".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# Templates CLIPS (p-video)
# ---------------------------------------------------------------------------

def face_cam_dilemma(
    character_desc: str, voice_desc: str, delivery: str, line_fr: str
) -> str:
    """Le perso face caméra pose son dilemme. Voix native, manière jouée.

    voice_desc doit être LA MÊME CHAÎNE pour tous les clips de ce perso.
    delivery : whispering / murmuring / hissing... (la manière de dire).
    """
    return _join(
        f"{character_desc}, facing the camera, close-up.",
        f"He speaks in French, {delivery}, with {voice_desc}, "
        f'and says exactly: "{line_fr}"',
        "Then he falls silent and keeps staring at the camera.",
        "Natural lip sync, minimal facial movement, slow blinks.",
        VOICE_ONLY_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def action_sequence(character_desc: str, action_desc: str, environment_desc: str) -> str:
    """Le perso avance dans l'aventure (la narration TTS sera mixée par-dessus)."""
    return _join(
        f"{character_desc} {action_desc}, seen from behind or in profile,",
        f"moving through {environment_desc}.",
        "Slow deliberate movement, the figure stays small in the frame.",
        AMBIENT_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def environment_showcase(environment_desc: str, danger_desc: str) -> str:
    """Plan d'environnement hostile (narration TTS mixée par-dessus)."""
    return _join(
        f"Establishing shot of {environment_desc}.",
        f"The danger is visible and physical: {danger_desc}.",
        "Subtle menacing motion within the scene: dust falling, faint tremors, "
        "unstable elements shifting slightly.",
        AMBIENT_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def fatal_outcome(character_desc: str, kill_desc: str, pov_reaction: str) -> str:
    """La mort en mouvement, POV : ce que le perso TE fait, comment TU réagis."""
    return _join(
        "First-person POV shot, the viewer is the victim.",
        f"{character_desc} {kill_desc}.",
        f"The viewer reacts: {pov_reaction}.",
        "Slow, deliberate, terrifying pacing.",
        AMBIENT_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def survival_outcome(character_desc: str, outcome_desc: str) -> str:
    """L'issue où l'on survit — mais qui reste angoissante."""
    return _join(
        "First-person POV shot, the viewer just survived.",
        f"{character_desc} {outcome_desc}.",
        "The tension does not release: the threat remains present.",
        AMBIENT_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def epilogue_other_path(other_character_desc: str, glimpse_desc: str) -> str:
    """« Si tu avais choisi l'autre... » — aperçu de l'autre chemin."""
    return _join(
        f"{other_character_desc} {glimpse_desc}.",
        "Dreamlike distant tone, as a vision of a path not taken.",
        AMBIENT_AUDIO,
        STATIC_CAMERA,
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )


def narrator_audition(voice_desc: str, line_fr: str) -> str:
    """Clip jetable d'audition : visuel minimal, la voix est le sujet."""
    return _join(
        "Almost black screen: faint embers drifting in darkness.",
        f"A narrator speaks in French, off-screen, with {voice_desc}, "
        f'and says exactly: "{line_fr}"',
        VOICE_ONLY_AUDIO,
        STATIC_CAMERA,
        NO_TEXT,
        VERTICAL,
    )


# ---------------------------------------------------------------------------
# Templates IMAGES (seedream)
# ---------------------------------------------------------------------------

def choice_image(option_desc: str, environment_desc: str) -> str:
    """L'image d'UN choix (deux images en succession par round)."""
    return _join(
        f"Dramatic still frame illustrating one option: {option_desc},",
        f"within {environment_desc}.",
        "Strong central composition, readable in half a second.",
        HORROR_STYLE,
        NO_TEXT,
        VERTICAL,
    )
