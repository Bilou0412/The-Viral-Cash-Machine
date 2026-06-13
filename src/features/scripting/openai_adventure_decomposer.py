"""OpenAI GPT adventure-script decomposer.

Transforme la prompt de l'utilisateur en `AdventureScript` validé (structured
output + validation Pydantic). Le JSON Schema dérivé de `AdventureScript` est
joint au prompt pour contraindre la sortie ; la validation Pydantic est l'arbitre
final, avec une passe d'auto-réparation (1 retry) en cas d'échec.
"""

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .adventure import AdventureScript

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

_STRUCTURE_RULES = """STRUCTURE:
- Exactly 3 rounds. Each round has exactly 2 choices and exactly ONE fatal choice
  (`is_fatal: true`), the other survives (`is_fatal: false`).
- The narrator has a FIXED pre-cloned voice — do NOT invent or describe a narrator
  voice. Only the two CHARACTER voice profiles are generated.
- `character_delivery` is an English manner of speaking (e.g. "whispering",
  "murmuring", "hissing").
- Use the provided French first names verbatim for `char_left_name` /
  `char_right_name`.
- INTRO personalization (per character):
  - `char_*_personality_fr`: ONE short, simple French sentence introducing who
    the character is (their nature/vibe). Plain words.
  - `char_*_intro_line_fr`: a SHORT anguishing French line the character says to
    the viewer to be picked — he says his OWN name and pleads/warns
    (e.g. "Moi, c'est Étienne. Choisis-moi... ou tu ne ressortiras pas.").
    The two characters must feel DIFFERENT (one pleads, one threatens)."""


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
    ) -> AdventureScript:
        """Generate and validate a 3-round adventure script.

        Args:
            prompt: User-provided theme / pitch.
            char_left_name: French first name of the left character.
            char_right_name: French first name of the right character.

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
            f"{_GOLDEN_RULES}\n\n{_STRUCTURE_RULES}\n\n"
            f"JSON Schema:\n{schema}"
        )
        user_msg = (
            f"Theme / pitch: {prompt}\n"
            f"Left character first name (French): {char_left_name}\n"
            f"Right character first name (French): {char_right_name}\n"
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
