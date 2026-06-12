"""Bibliothèque de prompts — le composant n°1 du système.

Chaque type d'asset a son template à slots. Les templates assemblent des blocs
réutilisables. Tout le format est une IMMERSION POV/FPS : le spectateur EST
quelqu'un qui suit le protagoniste (cf. EXTENSION_PLAN.md, doctrine POV/FPS).

RÈGLES D'OR (apprises en tests réels) :
1. Une ligne = une contrainte fonctionnelle. Court et dense, jamais dilué.
2. Dialogue exact entre guillemets, manière de dire AVANT la réplique.
   Répliques courtes (moins de paraphrase).
3. Description de voix réinjectée VERBATIM — jamais reformulée entre deux clips
   d'une même identité. C'est le mécanisme de cohérence vocale.
4. Ne JAMAIS mentionner ce qu'on ne veut pas voir (nommer = faire apparaître).
5. Jamais de texte demandé à l'image — le texte réel vient des overlays.
6. POV/FPS partout : nos mains visibles, le protagoniste toujours dans le cadre.
7. Visuels en ANGLAIS, dialogues en FRANÇAIS.
"""

# ---------------------------------------------------------------------------
# Blocs réutilisables — DA unique + grammaire POV
# ---------------------------------------------------------------------------

# La DA partagée par TOUS les assets (intro → fin), pour la cohérence visuelle.
DA = (
    "dark cinematic horror, photorealistic, heavily desaturated cold palette, "
    "deep crushed shadows, a single harsh handheld torch as the only light, "
    "wet glistening surfaces, drifting dust, fine film grain"
)

# Notre présence à la première personne (mains visibles, comme un FPS / l'intro).
POV_HANDS = "our own bare hands visible at the lower edge of the frame"

NO_TEXT = "No text, no lettering, no logos in the frame."

VOICE_ONLY_AUDIO = "Audio: voice only, no music, no ambience."

AMBIENT_AUDIO = "Audio: immersive ambience of the place, no music."

VERTICAL = "Vertical 9:16."


def _join(*parts: str) -> str:
    """Assemble les blocs non vides en un prompt compact."""
    return " ".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------------------
# Templates CLIPS (p-video) — immersion POV/FPS
# ---------------------------------------------------------------------------

def action_sequence(
    character_name: str, character_desc: str, action_desc: str, environment_desc: str
) -> str:
    """On SUIT le protagoniste qui avance devant nous (POV/FPS, caméra mobile)."""
    return _join(
        f"First-person POV, immersive FPS video-game perspective.",
        f"We follow close behind {character_name} ({character_desc}), always in "
        f"shot ahead of us, seen from behind, leading us as he {action_desc} "
        f"through {environment_desc}.",
        f"Forward walking camera motion, handheld sway, {POV_HANDS}.",
        DA + ".",
        AMBIENT_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


def environment_showcase(
    character_name: str, environment_desc: str, danger_desc: str
) -> str:
    """Le perso s'arrête devant nous ; on découvre le danger du lieu (POV)."""
    return _join(
        f"First-person POV. {character_name} halts a few steps ahead of us in "
        f"{environment_desc}.",
        f"From our viewpoint the danger looms: {danger_desc}.",
        f"Slow first-person sway, {POV_HANDS}.",
        DA + ".",
        AMBIENT_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


def character_choice(
    character_name: str,
    character_desc: str,
    voice_desc: str,
    delivery: str,
    line_fr: str,
) -> str:
    """Le perso s'arrête, se RETOURNE vers nous et nous balance les choix.

    Il s'adresse à nous (« tu »), caractérise les options, nous met la pression.
    `voice_desc` reste VERBATIM pour tous ses clips (règle d'or 3).
    `delivery` = manière (whispering / hissing / urgent low voice...).
    """
    return _join(
        f"First-person POV: {character_name} ({character_desc}) stops, turns and "
        f"faces us, close, locking eyes with the camera.",
        f"He speaks straight to us in French, {delivery}, with {voice_desc}, "
        f'pressing us to choose fast, and says exactly: "{line_fr}"',
        f"Intense eye contact, natural lip sync, {POV_HANDS}.",
        DA + ".",
        VOICE_ONLY_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


# Alias rétro-compat (ancien nom du template).
face_cam_dilemma = character_choice


def fatal_outcome(
    character_name: str, character_desc: str, kill_desc: str, pov_reaction: str
) -> str:
    """La mort en POV : ce que le perso nous fait, comment NOUS réagissons."""
    return _join(
        "First-person POV, we are the victim.",
        f"{character_name} ({character_desc}) {kill_desc}.",
        f"We react: {pov_reaction}, {POV_HANDS} flailing.",
        "Slow, deliberate, terrifying.",
        DA + ".",
        AMBIENT_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


def survival_outcome(
    character_name: str, character_desc: str, outcome_desc: str
) -> str:
    """On survit et on continue de suivre le perso — la tension reste (POV)."""
    return _join(
        "First-person POV, we just survived.",
        f"We follow {character_name} ({character_desc}) as he {outcome_desc}, "
        f"still ahead of us.",
        f"The threat lingers, {POV_HANDS}.",
        DA + ".",
        AMBIENT_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


def epilogue_other_path(
    other_name: str, other_desc: str, glimpse_desc: str
) -> str:
    """« Si tu avais choisi l'autre... » — aperçu POV de l'autre protagoniste."""
    return _join(
        f"First-person POV glimpse of {other_name} ({other_desc}) {glimpse_desc}.",
        f"Dreamlike, distant, a path not taken, {POV_HANDS}.",
        DA + ".",
        AMBIENT_AUDIO,
        NO_TEXT,
        VERTICAL,
    )


def narrator_audition(voice_desc: str, line_fr: str) -> str:
    """Clip jetable d'audition narrateur : visuel minimal, la voix est le sujet."""
    return _join(
        "Almost black screen: faint embers drifting in darkness.",
        f"A narrator speaks in French, off-screen, with {voice_desc}, "
        f'and says exactly: "{line_fr}"',
        VOICE_ONLY_AUDIO,
        "Static shot.",
        NO_TEXT,
        VERTICAL,
    )


# ---------------------------------------------------------------------------
# Templates IMAGES (seedream) — POV figé pour l'écran des choix
# ---------------------------------------------------------------------------

def choice_image(
    character_name: str, option_desc: str, environment_desc: str
) -> str:
    """Image POV d'UNE option (le perso la désigne devant nous)."""
    return _join(
        f"First-person POV still. Ahead of us in {environment_desc}: {option_desc}.",
        f"{character_name} is in frame, gesturing toward it, {POV_HANDS}.",
        "Strong central composition, readable in half a second.",
        DA + ".",
        NO_TEXT,
        VERTICAL,
    )
