"""Directeur artistique — le 1er agent-métier qui RÉÉCRIT le dossier.

Il consomme l'`AgentContext` (Phase B) — le brief + la tranche « scènes » — appelle
l'agent DA, puis **applique** son résultat au document : réécrit le prompt image
de chaque photo d'environnement (`{sceneid}_env`) et pose l'art direction globale.
Le doc est **revalidé** (mêmes invariants qu'à la sauvegarde) mais **pas persisté**
ici (la route le fait). Aucun asset n'est régénéré (réécriture seule, coût nul).

Patron réutilisable des métiers-agents qui muent le dossier (mirror `crew.py` pour
la sélection Fake/OpenAI, mais écrit dans `doc_json` au lieu d'un artefact à part).
"""

from __future__ import annotations

import os

from ....editor.document import ClipBrick, EditorDocument
from ....features.brief.model import Brief
from ....features.crew.fake_art_direction_agent import FakeArtDirectionAgent
from ....features.crew.model import ArtDirection, SceneRef
from ....features.crew.ports import ArtDirectionAgent
from .context import assemble_context
from .crew import DEFAULT_OPENAI_MODEL, AgentSource, agent_source

__all__ = ["AgentSource", "agent_source", "direct_art_direction", "get_art_direction_agent"]


def get_art_direction_agent(openai_key: str | None = None) -> ArtDirectionAgent:
    """Renvoie le directeur artistique OpenAI si une clé est donnée, sinon le Fake."""
    if not openai_key:
        return FakeArtDirectionAgent()
    from openai import OpenAI

    from ....features.crew.openai_art_direction_agent import OpenAIArtDirectionAgent

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIArtDirectionAgent(OpenAI(api_key=openai_key), model)


def _scene_refs(scenes: list[dict[str, object]]) -> list[SceneRef]:
    """La tranche « scènes » de l'AgentContext → entrées typées de l'agent DA."""
    return [
        SceneRef(
            id=str(s.get("id", "")),
            title=str(s.get("title", "")),
            environment=str(s.get("environment", "")),
        )
        for s in scenes
    ]


def _apply(doc: EditorDocument, art: ArtDirection) -> EditorDocument:
    """Applique l'art direction au doc : prompts d'environnement + art direction globale.

    Ne touche que les scènes renvoyées par l'agent (map `scene_id` →
    `environment_photo_ref` → brique). Revalide les invariants du doc avant de rendre.
    """
    if art.art_direction.strip():
        doc.global_context.art_direction = art.art_direction.strip()
    scene_by_id = {s.id: s for s in doc.scenes}
    brick_by_id = {b.id: b for b in doc.bricks}
    for sa in art.scenes:
        prompt = sa.environment_prompt.strip()
        scene = scene_by_id.get(sa.scene_id)
        if scene is None or not prompt:
            continue
        if art.art_direction.strip():
            scene.context.art_direction = art.art_direction.strip()
        env = brick_by_id.get(scene.environment_photo_ref)
        if isinstance(env, ClipBrick):
            env.image.params["prompt"] = prompt
    # Revalide (ids uniques, refs de scène résolues) comme à la sauvegarde.
    return EditorDocument.model_validate(doc.model_dump())


def direct_art_direction(
    doc: EditorDocument,
    brief: Brief,
    *,
    agent: ArtDirectionAgent | None = None,
    openai_key: str | None = None,
) -> EditorDocument:
    """Dirige le directeur artistique : réécrit l'identité visuelle du document.

    Renvoie le doc muté et revalidé (non persisté). Lève `CrewAgentError` si l'agent
    ne produit rien d'exploitable."""
    ctx = assemble_context("directeur_artistique", brief=brief, doc=doc)
    scenes = _scene_refs(ctx.dossier.get("scenes", []))
    ag = agent or get_art_direction_agent(openai_key)
    art = ag.direct(
        tone=brief.ton,
        platform=brief.plateforme,
        language=brief.langue,
        art_direction=str(ctx.dossier.get("art_direction", "")),
        scenes=scenes,
    )
    return _apply(doc, art)
