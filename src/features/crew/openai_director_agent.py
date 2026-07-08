"""Réalisateur OpenAI — assemble une PARTIE de vidéo depuis une description NL.

Brief métier : un réalisateur lit la description d'une partie (ex. l'intro) et la
DÉCOUPE en beats concrets, en choisissant les EFFETS dans le catalogue qu'on lui
montre (eye-open, countdown, nameplates). Il ne pose QUE des effets présents dans
la palette. Sortie JSON stricte parsée via Pydantic (mirror `openai_dialogue_agent`).
Convention : `sujet` en anglais (prompt visuel), `narration_fr` en français (parlé).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .model import FragmentPlan
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_SYSTEM = (
    "You are a DIRECTOR assembling ONE PART of a vertical 9:16 short (TikTok/Reels). "
    "Read the natural-language description and CUT it into concrete beats.\n"
    "You SEE a catalogue of montage EFFECTS — use ONLY effects from it:\n"
    "- montage.eye_open : an establishing shot revealed by an eye-open transition "
    "(set beat.eye_open=true, kind='photo').\n"
    "- montage.timer : a blurred 3-2-1 countdown screen (set beat.countdown=true, "
    "kind='photo', NO narration on that beat).\n"
    "- montage.nameplate : a name label anchored on a character's head (beat.nameplates "
    "= [{text, side:'left'|'right'}]).\n"
    "Each beat: {id, kind:'video'|'photo', sujet (ENGLISH visual prompt, subject-first), "
    "narration_fr (FRENCH spoken line, empty if none), duree_s (<=5), eye_open, countdown, "
    "nameplates}. Use French first names for people (never 'Character A'). Visual prompts "
    "in English, spoken lines in French.\n"
    'Return JSON {"part": <name>, "beats":[ ... ]}. Output JSON only.'
)


class OpenAIDirectorAgent:
    """Implémente `DirectorAgent` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def assemble(
        self, *, description: str, part: str = "intro",
        effects: list[str], language: str = "fr",
    ) -> FragmentPlan:
        catalogue = ", ".join(effects) or "(none)"
        user = (
            f"Part to assemble: {part}\n"
            f"Narration language: {language}\n"
            f"Available montage effects (catalogue): {catalogue}\n\n"
            f"Description of the part:\n{description.strip()}"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # erreur réseau / API
            raise CrewAgentError(f"Director request failed: {e}") from e
        content = resp.choices[0].message.content or ""
        try:
            data = json.loads(content)
            plan = FragmentPlan.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise CrewAgentError(f"Director returned unusable JSON: {e}") from e
        if not plan.beats:
            raise CrewAgentError("Director returned no beats.")
        if not plan.part:
            plan = plan.model_copy(update={"part": part})
        return plan
