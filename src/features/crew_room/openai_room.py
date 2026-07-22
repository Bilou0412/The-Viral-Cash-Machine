"""Atelier OpenAI — le réalisateur pose le contrat, chaque département remplit ses trous.

`OpenAIContractAgent` : 1 appel JSON → la liste des plans (le contrat). `OpenAIDrafter` :
1 appel JSON par département, **limité aux champs qu'il possède**. Import paresseux du SDK.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from ..scenes.model import CharacterPlan, ScenePlan, ShotCharacterPlan
from .model import (
    ContractShot,
    Draft,
    ReviewVerdict,
    RoomMemory,
    SceneBrief,
    SceneContract,
)
from .ports import DEPARTMENTS, CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

    from ..brief.model import Brief

_T = TypeVar("_T")

# Une scène = 9 appels OpenAI séquentiels (1 contrat + 4 départements + 4 révisions).
# La probabilité qu'UN échoue (JSON légèrement malformé, reset réseau, 5xx) n'est pas
# négligeable, et un seul échec faisait planter toute la scène (502). On retente donc
# chaque appel d'agent quelques fois ; une 2ᵉ tentative suffit presque toujours.
_MAX_ATTEMPTS = 3


def _retry(fn: Callable[[], _T]) -> _T:
    """Retente `fn` sur `CrewAgentError` (appel LLM ou parse), backoff court, puis relaie."""
    last: CrewAgentError | None = None
    for i in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except CrewAgentError as e:
            last = e
            if i < _MAX_ATTEMPTS - 1:
                time.sleep(0.4 * (i + 1))
    assert last is not None  # au moins une tentative a eu lieu
    raise last

_CONTRACT_SYSTEM = (
    "You are the DIRECTOR. Define the CONTRACT of ONE short vertical-video scene: the "
    "ordered list of shots to fill. Keep it tight (2 to 4 shots), static camera.\n"
    'Return JSON {"env_intention": "what the establishing photo shows (EN)", '
    '"shots":[{"id","beat":"what this shot is for (short)","kind":"video"|"photo"}]}. '
    "Output JSON only."
)

# Instruction par département : il ne remplit QUE ses champs.
_DEPT_SYSTEM: dict[str, str] = {
    "directeur_artistique": (
        "You are the ART DIRECTOR. Fill ONLY décor & lighting (ENGLISH). Return JSON "
        '{"env":{"decor","lighting"},"shots":{"<shot_id>":{"decor","lighting"}}} for every shot id.'
    ),
    "chef_operateur": (
        "You are the DoP. Fill ONLY framing (shot size + angle) and duration (seconds, 3-5), "
        'static camera. Return JSON {"shots":{"<shot_id>":{"framing","duration"}}} for every shot id.'
    ),
    "casting": (
        "You are CASTING & COSTUME. Reuse EXISTING bible characters for continuity, or introduce "
        "new ones. Return JSON {\"new_characters\":[{\"name\",\"appearance\",\"wardrobe\","
        "\"voice_id\",\"traits\"}],\"shots\":{\"<shot_id>\":[{\"name\",\"appearance\",\"wardrobe\","
        "\"expression\",\"action\"}]}}. Appearance/wardrobe in ENGLISH; French first names."
    ),
    "dialoguiste": (
        "You are the DIALOGUE writer. Fill ONLY narration (FRENCH, one short spoken line per shot). "
        'Return JSON {"shots":{"<shot_id>":{"narration"}}} for every shot id.'
    ),
}


def _context_blob(brief: Brief, scene_brief: SceneBrief, memory: RoomMemory) -> str:
    bible = ", ".join(f"{c.name} ({c.appearance})" for c in memory.bible) or "(aucun)"
    return (
        f"Brief — objectif: {brief.objectif or '(?)'}; audience: {brief.audience or '(?)'}; "
        f"ton: {brief.ton or '(?)'}; plateforme: {brief.plateforme}.\n"
        f"Scène — {scene_brief.title}: {scene_brief.intention}. "
        f"Décor amorcé: {scene_brief.environment or '(à définir)'}.\n"
        f"Mémoire — bible: {bible}. Déjà raconté: {memory.synopsis_so_far or '(rien)'}."
    )


def _shot_list(contract: SceneContract) -> str:
    return "; ".join(f"{s.id} ({s.beat})" for s in contract.shots) or "(aucun)"


def _scene_blob(scene: ScenePlan) -> str:
    """Sérialise la scène ASSEMBLÉE (tous les champs) pour la passe de révision."""
    lines = []
    for sh in scene.shots:
        who = ", ".join(c.name for c in sh.personnages) or "(aucun)"
        lines.append(
            f"- {sh.id}: cadrage='{sh.cadre.taille_plan}' caméra='{sh.camera.type}' "
            f"durée={sh.duree_s}s narration='{sh.narration_fr}' persos={who}"
        )
    return f"Scène « {scene.title} » assemblée :\n" + "\n".join(lines)


class _ContractOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    env_intention: str = ""
    shots: list[ContractShot] = []


class _CharOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    appearance: str = ""
    wardrobe: str = ""
    voice_id: str = ""
    traits: str = ""
    expression: str = ""
    action: str = ""


class _DraftOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    env: dict[str, str] = {}
    shots: dict[str, dict[str, str]] = {}
    new_characters: list[_CharOut] = []
    shot_characters: dict[str, list[_CharOut]] = {}


class _Chat:
    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def json(self, system: str, user: str, *, what: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # erreur réseau / API
            raise CrewAgentError(f"{what} failed: {e}") from e
        return resp.choices[0].message.content or ""


class OpenAIContractAgent:
    """Implémente `ContractAgent` via GPT (le réalisateur pose le contrat)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self._chat = _Chat(client, model)

    def define(
        self, *, brief: Brief, scene_brief: SceneBrief, memory: RoomMemory
    ) -> SceneContract:
        user = f"{_context_blob(brief, scene_brief, memory)}\n\nDéfinis le contrat de la scène."

        def _once() -> SceneContract:
            try:
                out = _ContractOut.model_validate_json(
                    self._chat.json(_CONTRACT_SYSTEM, user, what="Contract")
                )
            except ValidationError as e:
                raise CrewAgentError("Le contrat de scène est illisible. Réessaie.") from e
            sid = scene_brief.id or "s1"
            shots = [
                ContractShot(id=s.id or f"{sid}_sh{i + 1}", beat=s.beat, kind=s.kind)
                for i, s in enumerate(out.shots[:4])
            ]
            if not shots:
                raise CrewAgentError("Le réalisateur n'a défini aucun plan. Réessaie.")
            return SceneContract(env_intention=out.env_intention, shots=shots)

        return _retry(_once)


class OpenAIDrafter:
    """Implémente `Drafter` via GPT (un appel par département, champs possédés)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self._chat = _Chat(client, model)

    def fill(
        self,
        *,
        department: str,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> Draft:
        system = _DEPT_SYSTEM.get(department, "Fill your fields. JSON only.")
        user = (
            f"{_context_blob(brief, scene_brief, memory)}\n"
            f"Contrat — plans: {_shot_list(contract)}.\n\n"
            f"Remplis TON brouillon ({department}) en JSON."
        )
        return self._draft(department, system, user)

    def revise(
        self,
        *,
        department: str,
        scene: ScenePlan,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
        note: str = "",
    ) -> Draft:
        system = _DEPT_SYSTEM.get(department, "Fill your fields. JSON only.")
        directive = f"\nConsigne du superviseur : {note}" if note.strip() else ""
        user = (
            f"{_context_blob(brief, scene_brief, memory)}\n"
            f"{_scene_blob(scene)}{directive}\n\n"
            f"Voici la scène ASSEMBLÉE. Ajuste UNIQUEMENT tes champs ({department}) pour la "
            f"cohérence avec l'ensemble, puis renvoie le MÊME format JSON."
        )
        return self._draft(department, system, user, what=f"Revision '{department}'")

    def _draft(self, department: str, system: str, user: str, *, what: str = "") -> Draft:
        def _once() -> Draft:
            try:
                out = _DraftOut.model_validate_json(
                    self._chat.json(system, user, what=what or f"Draft '{department}'")
                )
            except ValidationError as e:
                raise CrewAgentError(
                    f"Le brouillon '{department}' est illisible. Réessaie."
                ) from e
            return Draft(
                department=department,
                env={k: v for k, v in out.env.items() if isinstance(v, str)},
                shots=out.shots,
                new_characters=[
                    CharacterPlan(name=c.name, appearance=c.appearance, wardrobe=c.wardrobe,
                                  voice_id=c.voice_id, traits=c.traits)
                    for c in out.new_characters if c.name.strip()
                ],
                shot_characters={
                    sid: [
                        ShotCharacterPlan(name=c.name, expression=c.expression, action=c.action)
                        for c in chars
                    ]
                    for sid, chars in out.shot_characters.items()
                },
            )

        return _retry(_once)


_REVIEW_SYSTEM = (
    "You are the DIRECTOR reviewing an ASSEMBLED short-vertical-video scene before shooting. "
    "Check coherence across departments: décor/lighting (art), framing/duration (DoP, 3-5s "
    "static camera), characters (casting), narration (French, one short line per shot, must "
    "name the character present). If everything is coherent, APPROVE. Otherwise, send back "
    "ONLY the departments that must fix something, with a short instruction each. "
    "Departments: directeur_artistique, chef_operateur, casting, dialoguiste.\n"
    'Return JSON {"ok": true|false, "redo": {"<department>": "instruction"}, "note": "one line"}. '
    "JSON only."
)


class _ReviewOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ok: bool = True
    redo: dict[str, str] = {}
    note: str = ""


class OpenAIReviewer:
    """Implémente `Reviewer` via GPT (le réalisateur relit et renvoie corriger, ciblé)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self._chat = _Chat(client, model)

    def review(
        self,
        *,
        scene: ScenePlan,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> ReviewVerdict:
        user = (
            f"{_context_blob(brief, scene_brief, memory)}\n"
            f"{_scene_blob(scene)}\n\n"
            "Relis la scène assemblée : valide, ou renvoie corriger des départements ciblés."
        )
        try:
            out = _ReviewOut.model_validate_json(self._chat.json(_REVIEW_SYSTEM, user, what="Review"))
        except ValidationError as e:
            raise CrewAgentError("La revue du superviseur est illisible. Réessaie.") from e
        # On ne garde que des départements CONNUS (le LLM peut halluciner une clé).
        redo = {d: note for d, note in out.redo.items() if d in DEPARTMENTS and note.strip()}
        return ReviewVerdict(ok=out.ok and not redo, redo=redo, note=out.note)
