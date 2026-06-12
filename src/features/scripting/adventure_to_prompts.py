"""Remplissage des slots : `AdventureScript` → prompts de `prompts.py`.

Module PUR (aucune I/O) : il prend un script validé et produit, champ par champ,
les chaînes de prompt que Step 1 enverra aux modèles. Preuve exécutable que
CHAQUE champ alimente le bon template (cf. EXTENSION_PLAN.md, phase S).

Tout est en POV/FPS : on suit UN personnage (le « happy path » choisi). Le perso
suivi fixe `name`/`desc`/`voice` réinjectés dans tous ses clips ; l'épilogue
montre l'AUTRE. Le mapping est paramétré par le côté suivi (`"left"`/`"right"`).
"""

from typing import List, Literal, NamedTuple

from . import prompts as P
from .adventure import AdventureScript, Choice, Round

Side = Literal["left", "right"]


class RoundPrompts(NamedTuple):
    """Tous les prompts visuels d'un round, dans l'ordre de la timeline."""

    action: str
    environment: str
    face_cam: str
    choice_images: tuple[str, str]
    fatal: str
    survival: str

    def as_list(self) -> List[str]:
        return [
            self.action,
            self.environment,
            self.face_cam,
            self.choice_images[0],
            self.choice_images[1],
            self.fatal,
            self.survival,
        ]


def round_prompts(
    rnd: Round, character_name: str, character_desc: str, voice_desc: str
) -> RoundPrompts:
    """Mappe un round + le perso suivi vers ses prompts POV/FPS.

    `voice_desc` passe tel quel (règle d'or 3 : cohérence vocale verbatim).
    """
    return RoundPrompts(
        action=P.action_sequence(
            character_name, character_desc, rnd.action_desc, rnd.environment_desc
        ),
        environment=P.environment_showcase(
            character_name, rnd.environment_desc, rnd.danger_desc
        ),
        face_cam=P.character_choice(
            character_name,
            character_desc,
            voice_desc,
            rnd.character_delivery,
            rnd.character_line_fr,
        ),
        choice_images=(
            P.choice_image(
                character_name, rnd.choices[0].image_desc, rnd.environment_desc
            ),
            P.choice_image(
                character_name, rnd.choices[1].image_desc, rnd.environment_desc
            ),
        ),
        fatal=P.fatal_outcome(
            character_name, character_desc, rnd.fatal_kill_desc, rnd.fatal_pov_reaction
        ),
        survival=P.survival_outcome(
            character_name, character_desc, rnd.survival_outcome_desc
        ),
    )


def _followed(script: AdventureScript, side: Side) -> tuple[str, str, str, str, str]:
    """(name, desc, voix, other_name, other_desc) pour le perso suivi."""
    if side == "left":
        return (
            script.char_left_name,
            script.char_left_desc,
            script.char_left_voice.description,
            script.char_right_name,
            script.char_right_desc,
        )
    return (
        script.char_right_name,
        script.char_right_desc,
        script.char_right_voice.description,
        script.char_left_name,
        script.char_left_desc,
    )


def script_prompts(script: AdventureScript, side: Side) -> List[RoundPrompts]:
    """Les 3 RoundPrompts du chemin suivi (`side`)."""
    name, desc, voice, _, _ = _followed(script, side)
    return [round_prompts(r, name, desc, voice) for r in script.rounds]


def epilogue_prompt(script: AdventureScript, side: Side) -> str:
    """« Si tu avais choisi l'autre... » — l'AUTRE perso (slot epilogue_other_path)."""
    _, _, _, other_name, other_desc = _followed(script, side)
    return P.epilogue_other_path(other_name, other_desc, script.epilogue_other_desc)
