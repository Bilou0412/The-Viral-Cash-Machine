"""Schéma du script d'aventure complet (format « L'Aventure », 3 rounds + épilogue).

FONDATION de la phase S : le structured output GPT remplit un `AdventureScript`,
qui à son tour remplit les slots des templates de `prompts.py`.

Style aligné sur src/videospec/models.py :
- Tout est immuable (frozen) et sérialisable JSON.
- `extra="forbid"` partout : le JSON Schema dérivé contraint le structured output LLM.

Conventions de langue (règle projet) :
- Champs `*_desc`, `*_delivery`, `image_desc` : ANGLAIS (visuels réinjectés dans les prompts).
- Champs `*_fr`, `label_fr` : FRANÇAIS (dialogue / narration parlés).
"""

import json
import sys
from pathlib import Path
from typing import Tuple

from pydantic import BaseModel, ConfigDict, model_validator


class _Spec(BaseModel):
    """Base commune : immuable, strict (cf. videospec._Spec)."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class VoiceProfile(_Spec):
    """Description de voix d'un personnage.

    `description` (EN) est réinjectée VERBATIM dans chaque prompt face-cam du
    même perso — c'est le mécanisme de cohérence vocale (règle d'or 3).
    """

    description: str


class Choice(_Spec):
    """Une des deux options d'un round."""

    label_fr: str      # FR — texte du choix énoncé par le narrateur
    image_desc: str    # EN — illustration de l'option (slot prompts.choice_image)
    is_fatal: bool


class Round(_Spec):
    """Un round d'aventure : action → environnement → dilemme → choix → issues."""

    action_desc: str               # EN — slot prompts.action_sequence
    action_narration_fr: str       # FR — voix narrateur par-dessus
    environment_desc: str          # EN — lieu hostile
    danger_desc: str               # EN — danger physique (slot environment_showcase)
    environment_narration_fr: str  # FR
    character_line_fr: str         # FR — réplique face-cam (slot face_cam_dilemma)
    character_delivery: str        # EN — whispering / murmuring / hissing (la manière)
    choices: Tuple[Choice, Choice]
    choice_narration_fr: str       # FR — le narrateur énonce les deux choix
    fatal_kill_desc: str           # EN — slot prompts.fatal_outcome (kill_desc)
    fatal_pov_reaction: str        # EN — réaction POV (slot fatal_outcome)
    fatal_narration_fr: str        # FR — « Si tu as choisi X... »
    survival_outcome_desc: str     # EN — slot prompts.survival_outcome
    survival_narration_fr: str     # FR

    @model_validator(mode="after")
    def _check_one_fatal(self) -> "Round":
        if len(self.choices) != 2:
            raise ValueError("un round doit avoir exactement 2 choix")
        fatals = sum(1 for c in self.choices if c.is_fatal)
        if fatals != 1:
            raise ValueError(
                f"un round doit avoir exactement UN choix fatal (trouvé {fatals})"
            )
        return self


class AdventureScript(_Spec):
    """Script complet d'une vidéo « Aventure » : 2 persos, 3 rounds, 1 épilogue."""

    char_left_name: str            # prénom FR
    char_right_name: str           # prénom FR
    char_left_desc: str            # EN — apparence (slots face_cam du perso gauche)
    char_right_desc: str           # EN
    char_left_voice: VoiceProfile
    char_right_voice: VoiceProfile
    # Intro personnalisée (R1) — un texte de caractère + une réplique angoissante
    # où le perso dit SON nom et tente de te convaincre (« choisis-moi »).
    char_left_personality_fr: str   # FR simple — qui il est, son caractère (1 phrase)
    char_right_personality_fr: str  # FR simple
    char_left_intro_line_fr: str    # FR — réplique d'intro angoissante (dit son nom)
    char_right_intro_line_fr: str   # FR
    transition_narration_fr: str   # FR — « Si tu as choisi Étienne... »
    rounds: Tuple[Round, Round, Round]   # EXACTEMENT 3
    epilogue_other_desc: str       # EN — slot prompts.epilogue_other_path (glimpse)
    epilogue_narration_fr: str     # FR — « Si tu avais choisi l'autre... »

    @model_validator(mode="after")
    def _check_rounds(self) -> "AdventureScript":
        if len(self.rounds) != 3:
            raise ValueError("un script d'aventure doit avoir exactement 3 rounds")
        return self


# ---------------------------------------------------------------------------
# Export JSON Schema — contrainte du structured output GPT (phase S)
# ---------------------------------------------------------------------------

DEFAULT_SCHEMA_PATH = "schemas/adventure.schema.json"


def export_schema(path: str = DEFAULT_SCHEMA_PATH) -> str:
    """Écrit le JSON Schema d'AdventureScript et retourne le chemin."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = AdventureScript.model_json_schema()
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCHEMA_PATH
    print(export_schema(target))
