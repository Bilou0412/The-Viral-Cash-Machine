"""Remplissage des slots : `AdventureScript` → prompts de `prompts.py`.

Module PUR (aucune I/O, aucun appel réseau) : il prend un script validé et
produit, champ par champ, les chaînes de prompt que Step 1 enverra aux modèles.
C'est la preuve exécutable que CHAQUE champ du schéma alimente le bon template
(cf. EXTENSION_PLAN.md, phase S — « Le script remplit les slots des templates »).

Le format suit UN personnage (le « happy path » choisi par le spectateur). Le
personnage suivi fixe `char_desc`/`voice` réinjectés VERBATIM dans tous ses
clips ; l'épilogue montre l'AUTRE personnage. Le mapping est donc paramétré par
le côté suivi (`"left"` ou `"right"`).
"""

from typing import List, Literal, NamedTuple

from . import prompts as P
from .adventure import AdventureScript, Choice, Round

Side = Literal["left", "right"]


class RoundPrompts(NamedTuple):
    """Tous les prompts visuels d'un round, dans l'ordre de la timeline."""

    action: str            # prompts.action_sequence
    environment: str       # prompts.environment_showcase
    face_cam: str          # prompts.face_cam_dilemma
    choice_images: tuple[str, str]  # prompts.choice_image (une par option)
    fatal: str             # prompts.fatal_outcome
    survival: str          # prompts.survival_outcome

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


def _choice_image(choice: Choice, environment_desc: str) -> str:
    return P.choice_image(choice.image_desc, environment_desc)


def round_prompts(
    rnd: Round, character_desc: str, voice_desc: str
) -> RoundPrompts:
    """Mappe un round + le perso suivi vers ses prompts visuels.

    `character_desc` et `voice_desc` sont ceux du perso suivi ; `voice_desc`
    passe tel quel (règle d'or 3 : cohérence vocale verbatim entre clips).
    """
    return RoundPrompts(
        action=P.action_sequence(
            character_desc, rnd.action_desc, rnd.environment_desc
        ),
        environment=P.environment_showcase(rnd.environment_desc, rnd.danger_desc),
        face_cam=P.face_cam_dilemma(
            character_desc,
            voice_desc,
            rnd.character_delivery,
            rnd.character_line_fr,
        ),
        choice_images=(
            _choice_image(rnd.choices[0], rnd.environment_desc),
            _choice_image(rnd.choices[1], rnd.environment_desc),
        ),
        fatal=P.fatal_outcome(
            character_desc, rnd.fatal_kill_desc, rnd.fatal_pov_reaction
        ),
        survival=P.survival_outcome(character_desc, rnd.survival_outcome_desc),
    )


def _followed(script: AdventureScript, side: Side) -> tuple[str, str, str]:
    """(desc, voix, desc de l'AUTRE) pour le perso suivi."""
    if side == "left":
        return script.char_left_desc, script.char_left_voice.description, script.char_right_desc
    return script.char_right_desc, script.char_right_voice.description, script.char_left_desc


def script_prompts(script: AdventureScript, side: Side) -> List[RoundPrompts]:
    """Les 3 RoundPrompts du chemin suivi (`side`)."""
    character_desc, voice_desc, _ = _followed(script, side)
    return [round_prompts(r, character_desc, voice_desc) for r in script.rounds]


def epilogue_prompt(script: AdventureScript, side: Side) -> str:
    """« Si tu avais choisi l'autre... » — l'AUTRE perso (slot epilogue_other_path)."""
    _, _, other_desc = _followed(script, side)
    return P.epilogue_other_path(other_desc, script.epilogue_other_desc)
