"""Décomposeur « Système expliqué » OpenAI — VISION, une passe.

On envoie l'IMAGE au modèle (vision) avec une consigne : identifier le système montré,
puis l'expliquer en N étapes ordonnées. Chaque étape → un plan COURT (sujet visuel EN,
narration FR). Sortie = `VideoPlan` (même IR que les scènes) ; le service applique ensuite
le split ≤ horizon. Convention langue : sujet/visuel EN (les modèles image attendent l'EN),
narration FR.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from ...editor.document import Cadre, Camera, IntentionGlobale, RenderMeta
from ..scenes.model import ScenePlan, ShotPlan, VideoPlan
from .ports import DEFAULT_STEPS, SystemExplainError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_LANG_LABELS = {"fr": "FRENCH", "en": "ENGLISH", "es": "SPANISH", "de": "GERMAN"}
_PLATFORM_LABELS = {"tiktok": "TikTok", "reels": "Reels", "shorts": "Shorts"}

_META = RenderMeta(
    ratio="9:16",
    fps=30,
    resolution="1080p",
    style_rendu="clean explanatory, high clarity",
    grain_etalonnage="neutral",
)


class _StepOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    narration: str = ""  # narration (langue demandée)
    visual: str = ""     # prompt visuel EN


class _PlanOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    system_name: str = ""
    system_desc: str = ""  # EN — description du système (photo d'établissement)
    steps: list[_StepOut] = []


def _lang(language: str) -> str:
    return _LANG_LABELS.get(language, language.upper() or "FRENCH")


def _platform(platform: str) -> str:
    return _PLATFORM_LABELS.get(platform, "TikTok/Reels/Shorts")


class OpenAISystemExplainer:
    """Implémente `SystemExplainer` via un modèle OpenAI à vision (structured JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def explain_system(
        self,
        image: str,
        *,
        hint: str = "",
        n_steps: int = DEFAULT_STEPS,
        language: str = "fr",
        platform: str = "tiktok",
    ) -> VideoPlan:
        n = max(1, n_steps)
        system = (
            f"You are a short-form vertical (9:16) explainer director for {_platform(platform)}. "
            "You are shown an IMAGE of a SYSTEM — it can be anything: a building, a construction "
            "site, a computer component, a crowd, a machine, an organisation. "
            "1) Identify the system. 2) Explain HOW IT WORKS or HOW IT IS BUILT as an ORDERED "
            f"list of EXACTLY {n} steps, from the base to the finished/running whole. "
            "Each step becomes ONE short shot (max 5 seconds). "
            f"Write 'narration' in {_lang(language)} (one short spoken sentence). "
            "Write 'visual' in ENGLISH (a short image-generation prompt, subject first, static "
            "camera). Return JSON: "
            '{"system_name","system_desc"(EN),"steps":[{"narration","visual"}]}'
        )
        user = hint.strip() or "Explain this system step by step."
        content = self._vision_json(system, user, image)
        try:
            parsed = _PlanOut.model_validate_json(content)
        except ValidationError as e:
            raise SystemExplainError(
                f"Réponse du modèle illisible (JSON inattendu). Détail : {e}"
            ) from e
        steps = [s for s in parsed.steps if s.visual.strip() or s.narration.strip()]
        if not steps:
            raise SystemExplainError(
                "Le modèle n'a extrait aucune étape exploitable de l'image."
            )
        title = parsed.system_name.strip() or hint.strip() or "Système expliqué"
        return VideoPlan(
            title=title,
            meta=_META,
            intention_globale=IntentionGlobale(
                genre="explainer court",
                ton="pédagogique, clair",
                arc_narratif=f"expliquer {title} étape par étape",
            ),
            scenes=[self._step_scene(i + 1, s, parsed.system_desc) for i, s in enumerate(steps)],
        )

    def _step_scene(self, i: int, step: _StepOut, system_desc: str) -> ScenePlan:
        visual = step.visual.strip() or system_desc or "the system"
        return ScenePlan(
            id=f"step{i}",
            title=f"Étape {i}",
            environment_desc=(system_desc.strip() or visual),
            location_ref="systeme",
            mood="clear, instructive",
            intention_scene=f"expliquer l'étape {i}",
            shots=[
                ShotPlan(
                    id=f"step{i}_sh1",
                    kind="video",
                    duree_s=4.0,
                    narration_fr=step.narration.strip(),
                    start_image=visual,
                    sujet=visual,
                    cadre=Cadre(taille_plan="medium shot", focale="50mm", angle_hauteur="eye level"),
                    camera=Camera(type="slow push in", vitesse="slow", depart_arrivee="from wide to detail"),
                    intention_plan=f"montrer l'étape {i}",
                )
            ],
        )

    def _vision_json(self, system: str, user: str, image: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user},
                            {"type": "image_url", "image_url": {"url": image}},
                        ],
                    },
                ],
            )
        except Exception as e:  # réseau / API (clé invalide, modèle sans vision, quotas…)
            raise SystemExplainError(
                "L'appel au décomposeur de système OpenAI a échoué "
                "(vérifie ta clé, un modèle à VISION dans OPENAI_MODEL, et tes quotas). "
                f"Détail : {e}"
            ) from e
        return resp.choices[0].message.content or ""
