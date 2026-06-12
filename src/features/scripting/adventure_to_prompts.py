"""Remplissage des slots : `AdventureScript` → prompts de `prompts.py`.

Module PUR (aucune I/O). Méthodologie image-first : chaque plan vidéo produit un
`VideoBeat(frame, motion)` — l'image de première frame (tout le visuel) ET le
prompt de mouvement (mouvement + dialogue). Les images de choix restent de
simples images.

Atomes VISUELS du script (→ frames) : char_desc, environment_desc, danger_desc,
image_desc. Atomes MOUVEMENT (→ motions) : action_desc, character_line_fr,
fatal_kill_desc/fatal_pov_reaction, survival_outcome_desc.

POV : on suit UN perso (chemin choisi) ; l'épilogue montre l'AUTRE.
"""

from typing import List, Literal, NamedTuple

from . import prompts as P
from .adventure import AdventureScript, Round

Side = Literal["left", "right"]


class VideoBeat(NamedTuple):
    """Un plan vidéo = sa première frame (image) + son mouvement (vidéo)."""

    frame: str   # prompt image (seedream) — tout le visuel
    motion: str  # prompt vidéo (image→vidéo p-video) — mouvement + dialogue


class RoundPrompts(NamedTuple):
    """Tous les prompts d'un round, dans l'ordre de la timeline."""

    action: VideoBeat
    environment: VideoBeat
    character: VideoBeat
    choice_images: tuple[str, str]   # 2 images (pas de vidéo)
    fatal: VideoBeat
    survival: VideoBeat

    def video_beats(self) -> List[VideoBeat]:
        return [self.action, self.environment, self.character, self.fatal, self.survival]

    def all_image_prompts(self) -> List[str]:
        """Toutes les images à générer (frames des vidéos + images de choix)."""
        return [b.frame for b in self.video_beats()] + list(self.choice_images)


def round_prompts(
    rnd: Round, character_name: str, character_desc: str, voice_desc: str
) -> RoundPrompts:
    """Mappe un round + le perso suivi vers ses VideoBeat + images de choix."""
    return RoundPrompts(
        action=VideoBeat(
            frame=P.frame_action(character_name, character_desc, rnd.environment_desc),
            motion=P.motion_action(character_name, rnd.action_desc),
        ),
        environment=VideoBeat(
            frame=P.frame_environment(
                character_name, rnd.environment_desc, rnd.danger_desc
            ),
            motion=P.motion_environment(character_name),
        ),
        character=VideoBeat(
            frame=P.frame_character(
                character_name, character_desc, rnd.environment_desc
            ),
            motion=P.motion_character(
                character_name, voice_desc, rnd.character_delivery, rnd.character_line_fr
            ),
        ),
        choice_images=(
            P.choice_image(character_name, rnd.choices[0].image_desc, rnd.environment_desc),
            P.choice_image(character_name, rnd.choices[1].image_desc, rnd.environment_desc),
        ),
        fatal=VideoBeat(
            frame=P.frame_fatal(character_name, character_desc, rnd.environment_desc),
            motion=P.motion_fatal(
                character_name, rnd.fatal_kill_desc, rnd.fatal_pov_reaction
            ),
        ),
        survival=VideoBeat(
            frame=P.frame_survival(character_name, character_desc, rnd.environment_desc),
            motion=P.motion_survival(character_name, rnd.survival_outcome_desc),
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


def epilogue_beat(script: AdventureScript, side: Side) -> VideoBeat:
    """L'épilogue (l'AUTRE perso) — frame + motion, comme tout plan vidéo."""
    _, _, _, other_name, other_desc = _followed(script, side)
    env = "a parallel passage fading into darkness"
    return VideoBeat(
        frame=P.frame_survival(other_name, other_desc, env),
        motion=P.motion_survival(other_name, script.epilogue_other_desc),
    )
