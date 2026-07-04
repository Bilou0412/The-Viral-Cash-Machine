"""OpenAI GPT adventure-script decomposer.

Transforme la prompt de l'utilisateur en `AdventureScript` validé (structured
output + validation Pydantic). Le JSON Schema dérivé de `AdventureScript` est
joint au prompt pour contraindre la sortie ; la validation Pydantic est l'arbitre
final, avec une passe d'auto-réparation (1 retry) en cas d'échec.
"""

import json
import os
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from .adventure import DEFAULT_ROUNDS, AdventureScript, Round

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
- HARD CHOICES — create real doubt: BOTH options must look reasonable and
  tempting. The fatal one is a TRAP: it must NOT look more dangerous than the
  other — often the "safer-looking" option is the deadly one. Never an obvious
  right answer; the viewer must genuinely hesitate.
- Exactly ONE choice is fatal (`is_fatal: true`). FATAL TWIST = the chosen
  COMPANION turns on the viewer and CAUSES the death. At that instant he is
  malicious: HE provokes it himself (shoves you, traps you, locks you in, triggers
  the danger onto you). The kill may be a bit far-fetched, but it is HIS doing —
  not bad luck nor the environment alone. POV: the viewer is his victim.
- `fatal_kill_desc` (EN): what the COMPANION physically does to kill/doom the
  viewer (he is the aggressor). `fatal_pov_reaction` (EN): our POV reaction as
  his victim.
- `fatal_narration_fr`: starts with "Si tu as choisi <l'option fatale>, " then
  tells how the companion turns on you and causes your death.
  `survival_narration_fr`: the viewer survives; the companion's chance to strike is
  denied; the journey continues, uneasy.
- `character_line_fr`: his spoken line for this round — helpful on the surface, but
  he may subtly steer you toward the fatal option (he is NOT fully trustworthy).
- DESERTED visuals: every `*_desc` / `image_desc` shows ONLY the companion and the
  place — NEVER other people, crowds, bystanders or extra figures.
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


# ===========================================================================
# Mode « chronologie procédurale » (LOT 1.6) — OPTIONNEL, feature-flag.
#
# But : pour un script long/variable, garder un FIL ROUGE cohérent en deux temps
#   1. une timeline hypothétique (arc planifié en connaissant N),
#   2. une génération round-par-round qui transporte un résumé courant des rounds
#      précédents.
# La logique PURE (résumé courant, réconciliation de longueur, assemblage final)
# vit dans des helpers module-level SANS `self` ni client → testables hors réseau.
# ===========================================================================

# Variable d'env qui sert de défaut quand l'argument explicite n'est pas passé.
_CHRONOLOGY_ENV = "VCM_CHRONOLOGY"


class _Timeline(BaseModel):
    """Arc hypothétique : une phrase-beat par round (descente → climax → issue)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    beats: tuple[str, ...]


def _chronology_default() -> bool:
    """Lit le flag chronologie depuis l'environnement (défaut quand arg implicite)."""
    return os.environ.get(_CHRONOLOGY_ENV, "").strip().lower() in {"1", "true", "yes"}


def _reconcile_timeline_length(beats: tuple[str, ...], n: int) -> tuple[str, ...]:
    """Force la timeline à exactement `n` beats.

    Tronque si trop longue ; complète avec un beat générique si trop courte.
    Helper PUR (aucun réseau) → permet une dégradation gracieuse sans re-demander.
    """
    beats = tuple(beats)
    if len(beats) > n:
        return beats[:n]
    if len(beats) < n:
        pad = tuple(
            f"Beat {i + 1} : la descente continue, la tension monte d'un cran."
            for i in range(len(beats), n)
        )
        return beats + pad
    return beats


def _running_summary(prior_rounds: list[Round]) -> str:
    """Construit le résumé courant de l'aventure à partir des rounds déjà générés.

    Helper PUR : transporte l'état narratif (lieu, événements, tension, dernière
    issue de survie) pour nourrir la génération du round suivant. Vide au début.
    """
    if not prior_rounds:
        return "C'est le tout premier round : l'aventure commence à l'entrée."

    lines: list[str] = [
        f"Résumé de l'aventure jusqu'ici ({len(prior_rounds)} round(s) déjà vécus) :"
    ]
    for idx, rnd in enumerate(prior_rounds, start=1):
        lines.append(
            f"- Round {idx} : action « {rnd.action_desc} » dans « "
            f"{rnd.environment_desc} » ; danger « {rnd.danger_desc} » ; "
            f"le viewer a survécu : « {rnd.survival_narration_fr} »"
        )
    last = prior_rounds[-1]
    lines.append(
        "Dernière issue (point de continuité — le round suivant DOIT en découler) : "
        f"« {last.survival_outcome_desc} »."
    )
    return "\n".join(lines)


def _assemble_script(
    intro_parts: "dict[str, object]", rounds: list[Round]
) -> AdventureScript:
    """Assemble un AdventureScript depuis les parties intro/épilogue + les rounds.

    Helper PUR (aucun réseau) : Pydantic est l'arbitre final de validité.
    `intro_parts` doit fournir toutes les clés non-`rounds` d'AdventureScript.
    """
    data: dict[str, object] = {**intro_parts, "rounds": tuple(rounds)}
    return AdventureScript.model_validate(data)


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
        chronology: bool | None = None,
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
            chronology: OPTIONAL feature-flag. When falsy (DEFAULT), the original
                single-call path runs UNCHANGED (golden/offline stability). When
                True, a two-phase « chronologie procédurale » path runs: a
                hypothetical timeline (arc planned knowing N) then a
                block-by-block generation carrying a running summary of prior
                rounds, for a coherent through-line on long scripts. If None, the
                `VCM_CHRONOLOGY` env var decides (default off).

        Returns:
            A validated AdventureScript.

        Raises:
            ValueError: If generation or validation fails after one retry.
        """
        use_chronology = _chronology_default() if chronology is None else chronology
        if use_chronology:
            return self._decompose_chronology(
                prompt,
                char_left_name,
                char_right_name,
                char_left_desc,
                char_right_desc,
                n_rounds,
            )

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
                resp = self.client.chat.completions.create(  # type: ignore[call-overload]
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except Exception as e:  # erreur réseau / API
                raise ValueError(f"Adventure decomposition request failed: {e}") from e

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

    # ------------------------------------------------------------------
    # Mode chronologie procédurale (OPTIONNEL) — orchestration réseau.
    # La logique pure est dans les helpers module-level ci-dessus ;
    # ces méthodes ne font qu'enchaîner les appels et déléguer.
    # ------------------------------------------------------------------

    def _chat_json(self, messages: "list[dict[str, str]]") -> str:
        """Un appel chat JSON ; renvoie le contenu brut. Erreurs réseau → ValueError."""
        try:
            resp = self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except Exception as e:  # erreur réseau / API
            raise ValueError(f"Adventure decomposition request failed: {e}") from e
        return resp.choices[0].message.content or ""

    def _gen_timeline(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        n_rounds: int,
    ) -> tuple[str, ...]:
        """Phase 1 : génère l'arc hypothétique (N beats), réconcilié à N."""
        sys_msg = (
            "You are a horror story architect. Plan the SHAPE of a first-person "
            "horror descent as a hypothetical timeline.\n"
            f"Return a JSON object {{\"beats\": [...]}} with EXACTLY {n_rounds} "
            "beat-sentences (French), one per round, describing the descent shape "
            "(start → rising tension → climax → resolution). Each beat is ONE short "
            "sentence. Output JSON only."
        )
        user_msg = (
            f"Theme / pitch: {prompt}\n"
            f"Companion followed (left): {char_left_name}; other: {char_right_name}\n"
            f"Plan EXACTLY {n_rounds} beats now."
        )
        raw = self._chat_json(
            [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ]
        )
        try:
            timeline = _Timeline.model_validate_json(raw)
            beats = timeline.beats
        except ValidationError:
            beats = ()
        return _reconcile_timeline_length(beats, n_rounds)

    def _gen_round(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        beat: str,
        running_summary: str,
        round_index: int,
        n_rounds: int,
    ) -> Round:
        """Phase 2 : génère UN Round contraint par son schéma + l'état courant."""
        schema = json.dumps(Round.model_json_schema(), ensure_ascii=False)
        sys_msg = (
            "You are a master architect of interactive horror short-form videos.\n"
            "Produce ONE adventure round as a single JSON object that validates "
            "against the provided JSON Schema. Output JSON only.\n\n"
            f"{_GOLDEN_RULES}\n\n{_STRUCTURE_RULES}\n\n"
            "FIL ROUGE: this round MUST follow logically from the running summary "
            "below — same place/continuity, escalating tension. Stay faithful to "
            "the planned beat for this round.\n\n"
            f"JSON Schema (Round):\n{schema}"
        )
        user_msg = (
            f"Theme / pitch: {prompt}\n"
            f"Companion followed: {char_left_name}; other: {char_right_name}\n"
            f"This is round {round_index + 1} of {n_rounds}.\n"
            f"Planned beat for this round: {beat}\n\n"
            f"{running_summary}\n\n"
            "Return the full Round JSON now."
        )
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ]
        last_error: Exception | None = None
        for attempt in range(2):
            raw = self._chat_json(messages)
            try:
                return Round.model_validate_json(raw)
            except ValidationError as e:
                last_error = e
                if attempt == 0:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "The Round JSON failed validation. Fix it and "
                                "return the corrected full Round JSON only.\n"
                                f"Validation errors:\n{e}"
                            ),
                        }
                    )
        raise ValueError(f"Round {round_index + 1} failed validation: {last_error}")

    def _gen_intro_parts(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        char_left_desc: str,
        char_right_desc: str,
        n_rounds: int,
        rounds: list[Round],
    ) -> "dict[str, object]":
        """Génère les champs intro/épilogue (tout sauf `rounds`) en un appel."""
        # Sous-schéma : AdventureScript sans la clé `rounds`.
        full_schema = AdventureScript.model_json_schema()
        props = {
            k: v for k, v in full_schema.get("properties", {}).items() if k != "rounds"
        }
        required = [r for r in full_schema.get("required", []) if r != "rounds"]
        intro_schema = {
            **{k: v for k, v in full_schema.items()
               if k not in {"properties", "required"}},
            "properties": props,
            "required": required,
        }
        schema = json.dumps(intro_schema, ensure_ascii=False)
        summary = _running_summary(rounds)
        sys_msg = (
            "You are a master architect of interactive horror short-form videos.\n"
            "Produce ONLY the intro/character/epilogue fields of an adventure "
            "script (NOT the rounds) as a single JSON object that validates "
            "against the provided JSON Schema. Output JSON only.\n\n"
            f"{_GOLDEN_RULES}\n\n{_STRUCTURE_RULES}\n\n"
            "CREATOR CHARACTER DESCRIPTIONS: when a description is provided for a "
            "character, you MUST respect it (its look and personality), adapt it "
            "to the dark cinematic horror DA, and translate the VISUAL part to "
            "English for `char_*_desc`; keep the personality for "
            "`char_*_personality_fr`. When a description is empty, invent a "
            "fitting character from the theme.\n\n"
            "The epilogue must be consistent with the adventure summary below.\n\n"
            f"JSON Schema (intro/epilogue fields only):\n{schema}"
        )
        user_msg = (
            f"Theme / pitch: {prompt}\n"
            f"Left character — first name: {char_left_name}; "
            f"creator description: {char_left_desc or '(none, invent it)'}\n"
            f"Right character — first name: {char_right_name}; "
            f"creator description: {char_right_desc or '(none, invent it)'}\n"
            f"The adventure has {n_rounds} rounds.\n\n"
            f"{summary}\n\n"
            "Return the intro/epilogue fields JSON now."
        )
        raw = self._chat_json(
            [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ]
        )
        parts: dict[str, object] = json.loads(raw)
        parts.pop("rounds", None)
        return parts

    def _decompose_chronology(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        char_left_desc: str,
        char_right_desc: str,
        n_rounds: int,
    ) -> AdventureScript:
        """Two-phase chronology generation (timeline → rounds-with-state → assemble)."""
        beats = self._gen_timeline(
            prompt, char_left_name, char_right_name, n_rounds
        )

        rounds: list[Round] = []
        for i in range(n_rounds):
            rnd = self._gen_round(
                prompt,
                char_left_name,
                char_right_name,
                beats[i],
                _running_summary(rounds),
                i,
                n_rounds,
            )
            rounds.append(rnd)

        intro_parts = self._gen_intro_parts(
            prompt,
            char_left_name,
            char_right_name,
            char_left_desc,
            char_right_desc,
            n_rounds,
            rounds,
        )
        try:
            return _assemble_script(intro_parts, rounds)
        except ValidationError as e:
            raise ValueError(
                f"Chronology adventure script failed final validation: {e}"
            ) from e
