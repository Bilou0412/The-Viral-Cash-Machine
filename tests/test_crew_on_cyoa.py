"""Les agents-métiers (crew) opèrent sur le CYOA v5 — « les agents construisent le moule ».

Depuis l'unification (CYOA-1), le format horreur produit un `EditorDocument` v5. Les
agents de RAFFINEMENT du contenu — directeur artistique (réécrit les prompts des photos
d'établissement) et dialoguiste (réécrit le texte parlé) — sont **agnostiques au format**
(ils lisent l'`AgentContext` assemblé depuis n'importe quel doc). Ils raffinent donc le
CYOA sans toucher à sa STRUCTURE (le moule est codé en dur ; l'IA remplit le fond, cf.
`.claude/rules/architecture.md`). On verrouille ici cette garantie, offline (Fakes).
"""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick
from src.features.brief.model import Brief
from src.features.scenes.scene_plan_to_document import scene_plan_to_document
from src.features.scripting.adventure_to_video_plan import adventure_to_video_plan
from src.features.scripting.fake_adventure_decomposer import FakeAdventureDecomposer
from src.studio.api.services.art_direction import direct_art_direction
from src.studio.api.services.context import assemble_context
from src.studio.api.services.dialogue import direct_dialogue


def _cyoa_doc(n_rounds: int = 2):
    script = FakeAdventureDecomposer().decompose_adventure("cave", "Léo", "Sam", n_rounds=n_rounds)
    return scene_plan_to_document(adventure_to_video_plan(script))


def _env_prompts(doc):
    return {b.id: str(b.image.params.get("prompt", "")) for b in doc.bricks
            if isinstance(b, ClipBrick) and b.id.endswith("_env")}


def test_dialoguiste_context_covers_every_cyoa_narration():
    """La tranche « narration » de l'AgentContext expose CHAQUE réplique du CYOA (par id)."""
    doc = _cyoa_doc()
    brief = Brief(objectif="horreur virale", ton="tendu", langue="fr")
    ctx = assemble_context("dialoguiste", brief=brief, doc=doc)
    units = ctx.dossier.get("narration", [])
    narr_children = [c for b in doc.bricks if isinstance(b, ClipBrick)
                     for c in b.children if c.role == "narration"]
    assert units, "le dialoguiste doit recevoir des répliques à réécrire"
    assert len(units) == len(narr_children)          # 1 unité de contexte par narration
    assert all(u.get("id") and u.get("text") for u in units)


def test_art_direction_rewrites_cyoa_establishment_prompts():
    """Le DA (agnostique au format) réécrit les prompts des photos d'établissement CYOA."""
    doc = _cyoa_doc()
    brief = Brief(objectif="horreur virale", ton="tendu", langue="fr")
    before = _env_prompts(doc)
    assert before, "le CYOA v5 doit exposer des photos d'établissement par scène"
    doc = direct_art_direction(doc, brief)           # Fake DA
    after = _env_prompts(doc)
    assert after.keys() == before.keys()
    assert any(after[k] != before[k] for k in before)  # au moins un prompt réécrit


def test_crew_keeps_the_cyoa_document_valid():
    """Après DA + dialoguiste, la STRUCTURE du moule tient (plans toujours valides)."""
    doc = _cyoa_doc()
    brief = Brief(objectif="horreur virale", ton="tendu", langue="fr")
    doc = direct_dialogue(direct_art_direction(doc, brief), brief)
    shots = [b for b in doc.bricks if isinstance(b, ClipBrick) and b.shot is not None]
    assert shots
    for b in shots:
        assert validate_clip(b) == {}, b.id
