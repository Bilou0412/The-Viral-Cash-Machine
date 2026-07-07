"""Table ronde OpenAI — voix persona (GPT) + synthèse structurée.

Chaque voix = un appel GPT avec un prompt système de métier, voyant le débat en
cours. Le synthétiseur lit tout le débat et en extrait la scène STRUCTURÉE (JSON
strict → `ScenePlan` v4). Import paresseux du SDK (miroir des agents existants).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from ..scenes.model import CharacterPlan, ScenePlan, ShotCharacterPlan, ShotPlan
from .model import RoomMemory, RoomResult, SceneBrief, Turn
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

    from ..brief.model import Brief

# Prompt système par voix — chacun parle EN CARACTÈRE, en 1-2 phrases (français).
_PERSONAS: dict[str, str] = {
    "realisateur": (
        "Tu es le RÉALISATEUR, tu modères la table ronde d'UNE scène de vidéo verticale "
        "courte. Cadre la scène depuis le brief + la mémoire, garde le rythme, et tranche. "
        "1-2 phrases."
    ),
    "directeur_artistique": (
        "Tu es le DIRECTEUR ARTISTIQUE. Propose le décor et la lumière (vocabulaire visuel "
        "ANGLAIS dans tes mots-clés). 1-2 phrases."
    ),
    "chef_operateur": (
        "Tu es le CHEF OPÉRATEUR. Propose les plans : taille de plan + cadrage, caméra "
        "STATIQUE. 1-2 phrases."
    ),
    "casting": (
        "Tu es le CASTING & COSTUME. Place les personnages présents en RÉUTILISANT la bible "
        "(continuité), ou introduis-en un neuf avec apparence + tenue. 1-2 phrases."
    ),
    "dialoguiste": (
        "Tu es le DIALOGUISTE. Propose la narration (FRANÇAIS), courte et parlée. 1-2 phrases."
    ),
}

_SYNTH_SYSTEM = (
    "You are the SCRIPT SUPERVISOR. From the writers' room discussion, output the FINAL "
    "scene as STRICT JSON. Visual fields in ENGLISH (image models expect English), "
    "narration in FRENCH.\n"
    'Return {"environment_desc","lighting","shots":[{"id","kind","framing","decor",'
    '"lighting","characters":[{"name","appearance","wardrobe","expression","action"}],'
    '"narration_fr","duration_s"}],"new_characters":[{"name","appearance","wardrobe",'
    '"voice_id","traits"}]}.\n'
    "2 to 4 shots, STATIC camera. Reuse EXISTING bible names for recurring characters; put "
    "ONLY genuinely new characters in new_characters. Output JSON only."
)


def _context_blob(brief: Brief, scene_brief: SceneBrief, memory: RoomMemory) -> str:
    bible = ", ".join(f"{c.name} ({c.appearance})" for c in memory.bible) or "(aucun)"
    return (
        f"Brief — objectif: {brief.objectif or '(?)'}; audience: {brief.audience or '(?)'}; "
        f"ton: {brief.ton or '(?)'}; plateforme: {brief.plateforme}.\n"
        f"Scène — {scene_brief.title}: {scene_brief.intention}. "
        f"Décor amorcé: {scene_brief.environment or '(à définir)'}.\n"
        f"Mémoire — bible: {bible}. Déjà raconté: {memory.synopsis_so_far or '(rien)'}."
    )


def _transcript_text(transcript: list[Turn]) -> str:
    return "\n".join(f"{t.role}: {t.message}" for t in transcript) or "(la discussion commence)"


class _ShotCharOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    appearance: str = ""
    wardrobe: str = ""
    expression: str = ""
    action: str = ""


class _ShotOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = ""
    kind: str = "video"
    framing: str = ""
    decor: str = ""
    lighting: str = ""
    narration_fr: str = ""
    duration_s: float = 4.0
    characters: list[_ShotCharOut] = []


class _CharOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    appearance: str = ""
    wardrobe: str = ""
    voice_id: str = ""
    traits: str = ""


class _SceneOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    environment_desc: str = ""
    lighting: str = ""
    shots: list[_ShotOut] = []
    new_characters: list[_CharOut] = []


class OpenAIRoomVoice:
    """Implémente `RoomVoice` via GPT (un appel par prise de parole)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def speak(
        self, *, role: str, brief: Brief, scene_brief: SceneBrief,
        memory: RoomMemory, transcript: list[Turn],
    ) -> str:
        system = _PERSONAS.get(role, "Tu participes à la table ronde. 1-2 phrases (français).")
        user = (
            f"{_context_blob(brief, scene_brief, memory)}\n\n"
            f"Discussion jusqu'ici :\n{_transcript_text(transcript)}\n\n"
            f"Ta réplique ({role}) :"
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # erreur réseau / API — une voix muette ne bloque pas
            raise CrewAgentError(f"Room voice '{role}' failed: {e}") from e
        return resp.choices[0].message.content or ""


class OpenAISceneSynthesizer:
    """Implémente `SceneSynthesizer` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def synthesize(
        self, *, brief: Brief, scene_brief: SceneBrief,
        memory: RoomMemory, transcript: list[Turn],
    ) -> RoomResult:
        user = (
            f"{_context_blob(brief, scene_brief, memory)}\n\n"
            f"Discussion complète :\n{_transcript_text(transcript)}\n\n"
            "Produis la scène finale en JSON."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYNTH_SYSTEM},
                    {"role": "user", "content": user},
                ],
            )
            out = _SceneOut.model_validate_json(resp.choices[0].message.content or "")
        except ValidationError as e:
            raise CrewAgentError("La synthèse de scène est illisible. Réessaie.") from e
        except Exception as e:
            raise CrewAgentError(f"Scene synthesis failed: {e}") from e
        if not out.shots:
            raise CrewAgentError("La table ronde n'a produit aucun plan. Réessaie.")

        sid = scene_brief.id or "s1"
        shots = [
            ShotPlan(
                id=s.id or f"{sid}_sh{i + 1}",
                kind="photo" if s.kind.strip().lower() == "photo" else "video",
                visual_desc=s.decor,
                motion_desc="static camera",
                narration_fr=s.narration_fr,
                duration_s=max(2.0, min(6.0, s.duration_s or 4.0)),
                decor=s.decor, lighting=s.lighting, framing=s.framing,
                characters=[
                    ShotCharacterPlan(
                        name=c.name, appearance=c.appearance, wardrobe=c.wardrobe,
                        expression=c.expression, action=c.action,
                    )
                    for c in s.characters
                ],
            )
            for i, s in enumerate(out.shots[:4])
        ]
        scene = ScenePlan(
            id=sid, title=scene_brief.title,
            environment_desc=out.environment_desc or scene_brief.environment,
            lighting=out.lighting, context_text=scene_brief.intention,
            shots=shots,
        )
        new_chars = [
            CharacterPlan(
                name=c.name, appearance=c.appearance, wardrobe=c.wardrobe,
                voice_id=c.voice_id, traits=c.traits,
            )
            for c in out.new_characters if c.name.strip()
        ]
        return RoomResult(scene=scene, new_characters=new_chars, transcript=transcript)
