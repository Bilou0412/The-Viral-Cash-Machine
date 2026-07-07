"""Générateur de hooks OpenAI — N ouvertures concurrentes sur des angles distincts.

Structured-output JSON. Accroche (`hook_text`) en langue cible ; prompt visuel
(`first_shot_prompt`) en anglais (attendu par les modèles image). Import `openai`
paresseux (absent hors conteneur) — instancié par la factory du service.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from .model import HookVariant
from .ports import DEFAULT_N_VARIANTS, ViralityError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_LANG_LABELS = {"fr": "FRENCH", "en": "ENGLISH", "es": "SPANISH", "de": "GERMAN"}


class _HookOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    angle: str = ""
    hook_text: str = ""
    first_shot_prompt: str = ""


class _HooksOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hooks: list[_HookOut] = []


class OpenAIHookGenerator:
    """Implémente `HookVariantGenerator` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def generate_hooks(
        self,
        pitch: str,
        *,
        n: int = DEFAULT_N_VARIANTS,
        format_id: str = "scenes",
        language: str = "fr",
    ) -> list[HookVariant]:
        lang = _LANG_LABELS.get(language, language.upper() or "FRENCH")
        count = max(1, n)
        system = (
            "You are a viral short-form (9:16) hook writer for TikTok/Reels/Shorts. "
            f"Given ONE idea, produce EXACTLY {count} COMPETING opening hooks — the first "
            "~2 seconds that decide retention — each on a DIFFERENT angle (e.g. shock "
            "promise, in medias res, countdown, direct question, POV). Distinct angles, "
            "no overlap.\n"
            'Return JSON {"hooks":[{'
            f'"angle"(short, {lang}),"hook_text"(the spoken/on-idea promise, {lang}, ONE '
            'punchy line <= 12 words),"first_shot_prompt"(the opening frame as an ENGLISH '
            "image prompt, vertical 9:16, no on-screen text)}]}. Output JSON only."
        )
        user = f"Idea: {pitch}\nFormat: {format_id}\nWrite EXACTLY {count} hooks now."
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # réseau / clé / quota
            raise ViralityError(
                "La génération des hooks a échoué (vérifie ta clé OpenAI, le modèle et "
                f"tes quotas). Détail : {e}"
            ) from e
        content = resp.choices[0].message.content or ""
        try:
            out = _HooksOut.model_validate_json(content)
        except ValidationError as e:
            raise ViralityError("Réponse de hooks illisible.") from e
        variants = [
            HookVariant(
                id=f"hook{i + 1}",
                angle=h.angle,
                hook_text=h.hook_text,
                first_shot_prompt=h.first_shot_prompt,
            )
            for i, h in enumerate(out.hooks[:count])
            if h.hook_text.strip() or h.first_shot_prompt.strip()
        ]
        if not variants:
            raise ViralityError("Aucun hook exploitable généré ; reformule l'idée.")
        return variants
