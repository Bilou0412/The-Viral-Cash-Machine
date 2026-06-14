"""OpenAI GPT adventure-script decomposer.

Transforme la prompt de l'utilisateur en `AdventureScript` validé (structured
output + validation Pydantic). Le JSON Schema dérivé de `AdventureScript` est
joint au prompt pour contraindre la sortie ; la validation Pydantic est l'arbitre
final, avec une passe d'auto-réparation (1 retry) en cas d'échec.
"""

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .adventure import DEFAULT_ROUNDS, AdventureScript

if TYPE_CHECKING:  # `openai` n'est pas installé hors conteneur — import paresseux.
    from openai import OpenAI

# Les 7 règles d'or (cf. prompts.py docstring) encodées pour le modèle.
_GOLDEN_RULES = """RULES (each is a hard constraint, not a suggestion):
1. One line = one functional constraint. Keep descriptions short and dense, never diluted.
2. Character lines (`*_fr`) are SHORT spoken French sentences, exactly what is said.
3. Voice profiles (`char_*_voice.description`) are in ENGLISH, distinctive and
   evocative (timbre, pace, texture); they are reused verbatim for that character.
4. NEVER name what must not appear on screen; phrase visuals in the positive.
5. NEVER ask for text/lettering in any image (`image_desc`, `*_desc`); on-screen
   text is added later as overlays.
6. Horror tone: dark, cinematic, oppressive, tense. Safe horror wording
   (weathered, ashen, pale, aged) over gore.
7. ALL visual/delivery fields are in ENGLISH; ALL spoken fields (`*_fr`,
   `label_fr`) are in FRENCH.
8. SIMPLE, EVERYDAY French for every spoken field — plain common words, short
   sentences, no literary or convoluted phrasing. It must sound natural and be
   instantly understood.
9. FIL ROUGE (through-line): the whole script MUST make sense as one coherent
   descent — each round follows logically from the previous survival, the
   narrator's lines are consistent, nothing is random or absurd."""

_STRUCTURE_RULES = """STRUCTURE & STORY LOGIC (read carefully):
- The viewer picks ONE companion in the intro, then FOLLOWS that single companion
  (the LEFT character) through the whole horror adventure. The rounds are that
  ONE journey — NOT a repeated choice between the two characters.
- Each round = the viewer + the companion advancing. The round's 2 choices are
  ADVENTURE DECISIONS (which path / which action), e.g. "le tunnel qui monte" vs
  "passer par l'eau". NEVER frame a choice as "follow Louis vs follow Pierre".
- `choices[].label_fr`: a short ADVENTURE option (a path or an action), no name.
- Exactly ONE choice is fatal (`is_fatal: true`). FATAL = the VIEWER dies (POV);
  SAFE = the viewer continues. The companion REACTS (warns, pulls you) but does
  NOT 'disappear' as the outcome.
- `fatal_narration_fr`: describes the VIEWER's death (POV, what kills you).
  `survival_narration_fr`: the viewer survives and the journey continues.
- `character_line_fr`: the companion's spoken advice/reaction for this round,
  consistent with his personality (he helps you read the danger).
- `choice_narration_fr`: the narrator clearly PRESENTS the two options, naming
  each one ("À gauche…, à droite… — choisis"), so each can be shown with its image.
- `transition_narration_fr`: MUST start with "Si tu as choisi {char_left_name}, "
  then describe the action/environment the viewer is heading into (this plays over
  a zoom on the chosen companion at the entry of the adventure).
- The narrator has a FIXED pre-cloned voice — do NOT invent a narrator voice.
- `character_delivery` = English manner of speaking ("whispering", "hissing"…).
- Use the provided French first names verbatim.
- INTRO (per character):
  - `char_*_personality_fr`: ONE short simple French sentence (their nature).
  - INTRO DIALOGUE — the two lines form a SHORT exchange (their order is
    randomized at render): `char_left_intro_line_fr` = an ANGUISHING piece of
    ADVICE the character gives the viewer about the descent (1 sentence);
    `char_right_intro_line_fr` = a SHORT reply (a few words). They must feel
    different. They do NOT say "choisis-moi" (the narrator handles the choice)."""


class OpenAIAdventureDecomposer:
    """Decomposes a user prompt into a validated AdventureScript via OpenAI GPT."""

    def __init__(self, client: "OpenAI", model: str):
        """Initialize with an OpenAI client and a model id.

        Args:
            client: Authenticated OpenAI client.
            model: Model identifier (e.g., "gpt-5.4-mini").
        """
        self.client = client
        self.model = model

    def decompose_adventure(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        char_left_desc: str = "",
        char_right_desc: str = "",
        n_rounds: int = DEFAULT_ROUNDS,
    ) -> AdventureScript:
        """Generate and validate an N-round adventure script.

        Args:
            prompt: User-provided theme / pitch.
            char_left_name / char_right_name: French first names.
            char_left_desc / char_right_desc: OPTIONAL creator descriptions
                (appearance + personality). Respected & adapted if given.
            n_rounds: number of choice-sequences (rounds). The JSON Schema now
                allows a variable-length array, so the count is enforced in prose
                here and arbitrated by Pydantic (with the existing retry pass).

        Returns:
            A validated AdventureScript.

        Raises:
            ValueError: If generation or validation fails after one retry.
        """
        schema = json.dumps(
            AdventureScript.model_json_schema(), ensure_ascii=False
        )
        sys_msg = (
            "You are a master architect of interactive horror short-form videos.\n"
            "Produce a complete adventure script as a single JSON object that "
            "validates against the provided JSON Schema. Output JSON only.\n\n"
            f"Produce EXACTLY {n_rounds} rounds in `rounds` — no more, no less.\n\n"
            f"{_GOLDEN_RULES}\n\n{_STRUCTURE_RULES}\n\n"
            "CREATOR CHARACTER DESCRIPTIONS: when a description is provided for a "
            "character, you MUST respect it (its look and personality), adapt it "
            "to the dark cinematic horror DA, and translate the VISUAL part to "
            "English for `char_*_desc`; keep the personality for "
            "`char_*_personality_fr`. When a description is empty, invent a "
            "fitting character from the theme.\n\n"
            f"JSON Schema:\n{schema}"
        )
        user_msg = (
            f"Theme / pitch: {prompt}\n"
            f"Left character — first name: {char_left_name}; "
            f"creator description: {char_left_desc or '(none, invent it)'}\n"
            f"Right character — first name: {char_right_name}; "
            f"creator description: {char_right_desc or '(none, invent it)'}\n"
            "Return the full AdventureScript JSON now."
        )

        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]

        # Première tentative + une passe d'auto-réparation.
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except Exception as e:  # erreur réseau / API
                raise ValueError(f"Adventure decomposition request failed: {e}")

            raw = resp.choices[0].message.content or ""
            try:
                return AdventureScript.model_validate_json(raw)
            except ValidationError as e:
                last_error = e
                if attempt == 0:
                    # On renvoie l'erreur au modèle pour qu'il se corrige.
                    messages.append({"role": "assistant", "content": raw})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "The JSON failed validation. Fix it and return "
                                "the corrected full AdventureScript JSON only.\n"
                                f"Validation errors:\n{e}"
                            ),
                        }
                    )

        raise ValueError(
            f"Adventure script failed validation after retry: {last_error}"
        )
