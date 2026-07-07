"""Assembleur de contexte — le « dossier de briefing » de chaque agent-métier.

La question que le producteur s'est posée : *de quelles données chaque agent a
besoin pour prendre les meilleures décisions ?* Ce module y répond en assemblant,
pour un rôle donné, exactement sa tranche :

- le **Brief** du producteur (toujours) — objectif/audience/plateforme/durée/coût ;
- la **tranche du dossier** (l'`EditorDocument`) pertinente pour ce métier
  (le DA voit les décors, le chef op les plans, le dialoguiste la narration…) ;
- le **manifeste d'outils** (les contrats de capacité `registry.CONTRACTS` :
  champs + modèles préférés) des seuls kinds que ce métier touche ;
- ses **références** (sa fiche `CrewRole`).

C'est le *seam* où branchera le pipeline d'agents (chaque passe consomme un
`AgentContext`). Vit dans `studio` (peut importer `features` + `editor` ; l'inverse
est interdit). Aucun appel réseau — pur et testable hors-ligne.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from ....editor.document import ClipBrick
from ....features.brief.model import Brief
from ....features.compositing.registry import CONTRACTS
from ....features.crew import role_by_key

if TYPE_CHECKING:
    from ....editor.document import EditorDocument


class ToolCard(BaseModel):
    """Un outil du manifeste : un contrat de capacité aplati pour un agent."""

    kind: str
    fields: list[dict[str, Any]] = Field(default_factory=list)
    preferred_models: list[str] = Field(default_factory=list)


class AgentContext(BaseModel):
    """Le paquet de contexte d'un agent-métier (son dossier de briefing)."""

    role: str
    brief: Brief
    dossier: dict[str, Any] = Field(default_factory=dict)
    tools: list[ToolCard] = Field(default_factory=list)
    refs: dict[str, str] = Field(default_factory=dict)


# Quels kinds d'outils chaque métier manipule (les autres n'en ont pas besoin).
_ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "directeur_artistique": ("image",),
    "chef_operateur": ("video",),
    "inge_son": ("voice",),
    "tournage": ("image", "video", "voice"),
}


def _tool_card(kind: str) -> ToolCard:
    contract = CONTRACTS[kind]
    return ToolCard(
        kind=kind,
        fields=[
            {"name": f.name, "required": f.required, "label": f.label, "help": f.help}
            for f in contract.fields
        ],
        preferred_models=list(contract.preferred_models),
    )


# ── Extracteurs de tranches du dossier ──────────────────────────────────────

def _synopsis(doc: EditorDocument) -> str:
    """La trame : contexte global, à défaut la concaténation des textes de scène."""
    text = doc.global_context.text.strip()
    if text:
        return text
    parts = [s.context.text.strip() for s in doc.scenes if s.context.text.strip()]
    return " ".join(parts)[:400]


def _brick_prompt(doc: EditorDocument, brick_id: str) -> str:
    """Le prompt visuel d'une brique (sa photo/plan) par id, ou vide."""
    for b in doc.bricks:
        if b.id == brick_id and isinstance(b, ClipBrick):
            val = b.image.params.get("prompt") or b.image.params.get("image")
            return val.strip() if isinstance(val, str) else ""
    return ""


def _scenes_view(doc: EditorDocument) -> list[dict[str, Any]]:
    """Une vue par scène : titre, intention, décor, nombre de plans."""
    return [
        {
            "id": s.id,
            "title": s.title,
            "intention": s.context.text,
            "environment": _brick_prompt(doc, s.environment_photo_ref),
            "n_shots": len(s.shot_ids),
            "shot_ids": list(s.shot_ids),
        }
        for s in doc.scenes
    ]


def _narration_lines(doc: EditorDocument) -> list[str]:
    """Toutes les répliques/narrations (le texte parlé) du document, dans l'ordre."""
    return [u["text"] for u in _narration_units(doc)]


def _narration_units(doc: EditorDocument) -> list[dict[str, str]]:
    """Le texte parlé PORTEUR de l'id de son enfant audio (pour réécrire par id).

    Le dialoguiste doit relocaliser chaque réplique sur le bon `AudioChild` — la
    liste plate de textes ne suffit pas, on garde donc `{id, text}` par enfant.
    """
    units: list[dict[str, str]] = []
    for brick in doc.bricks:
        if isinstance(brick, ClipBrick):
            for child in brick.children:
                text = child.params.get("text")
                if isinstance(text, str) and text.strip():
                    units.append({"id": child.id, "text": text.strip()})
    return units


def _total_duration(doc: EditorDocument) -> float:
    """La durée totale posée sur la timeline (somme des placements de briques)."""
    return round(
        sum(
            b.placement.duration
            for b in doc.bricks
            if isinstance(b, ClipBrick) and b.placement.duration > 0
        ),
        2,
    )


def _dossier(role: str, doc: EditorDocument | None) -> dict[str, Any]:
    """La tranche du dossier pertinente pour ce métier (vide si pas de document)."""
    if doc is None:
        return {}
    characters = dict(doc.global_context.characters)
    if role == "scenariste":
        return {"synopsis": _synopsis(doc), "characters": characters}
    if role == "directeur_artistique":
        return {
            "art_direction": doc.global_context.art_direction,
            "scenes": [
                {"id": s["id"], "title": s["title"], "environment": s["environment"]}
                for s in _scenes_view(doc)
            ],
        }
    if role == "chef_operateur":
        return {
            "scenes": [
                {
                    "id": s["id"], "title": s["title"],
                    "intention": s["intention"], "n_shots": s["n_shots"],
                }
                for s in _scenes_view(doc)
            ]
        }
    if role in ("dialoguiste", "inge_son"):
        # Porteur des ids d'enfants audio → le dialoguiste réécrit par id.
        return {"narration": _narration_units(doc), "characters": characters}
    if role == "tournage":
        return {"n_scenes": len(doc.scenes), "n_bricks": len(doc.bricks)}
    if role == "monteur":
        return {"scenes": _scenes_view(doc), "total_duration_s": _total_duration(doc)}
    if role == "attache_presse":
        narration = _narration_lines(doc)
        return {
            "title": doc.title,
            "synopsis": _synopsis(doc),
            "hook": narration[0] if narration else "",
        }
    return {}  # producteur : produit le brief, pas de tranche de dossier


def assemble_context(
    role: str, *, brief: Brief, doc: EditorDocument | None = None
) -> AgentContext:
    """Assemble le dossier de briefing d'un agent : brief + tranche + outils + refs.

    Lève ``KeyError`` si le rôle n'existe pas dans le casting (le caller décide du
    code HTTP). Sans ``doc``, la tranche de dossier est vide (cas amont : le
    producteur/scénariste avant que le document n'existe)."""
    crew_role = role_by_key(role)
    if crew_role is None:
        raise KeyError(role)
    tools = [_tool_card(k) for k in _ROLE_TOOLS.get(role, ())]
    refs = {
        "title": crew_role.title,
        "subtitle": crew_role.subtitle,
        "produces": crew_role.produces,
        "phase": crew_role.phase,
        "kind": crew_role.kind,
    }
    return AgentContext(
        role=role, brief=brief, dossier=_dossier(role, doc), tools=tools, refs=refs
    )
