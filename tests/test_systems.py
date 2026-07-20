"""Format « Système expliqué » (#3) — offline, via le Fake (aucune clé OpenAI).

Verrouille les invariants de STRUCTURE : image → N étapes, chaque plan ≤ horizon (5 s),
narration FR + sujet visuel EN présents, et le document final est valide sur le rail
commun (`scene_plan_to_document` → EditorDocument).
"""

import pytest

pytest.importorskip("pydantic")

from src.editor import document_to_spec
from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick, EditorDocument
from src.features.assets.models import VIDEO_MODEL, max_coherent_duration_s
from src.features.scenes.scene_plan_to_document import scene_plan_to_document
from src.features.systems.fake_system_explainer import FakeSystemExplainer
from src.studio.api.services.formats import build_format_document
from src.studio.api.services.systems import generate_system_plan

_IMG = "https://example.com/chantier.png"


def test_explainer_produces_one_step_per_scene():
    """N étapes demandées → N scènes, chacune avec au moins un plan court."""
    plan = FakeSystemExplainer().explain_system(_IMG, hint="comment on construit une maison", n_steps=3)
    assert plan.title == "comment on construit une maison"
    assert len(plan.scenes) == 3
    for scene in plan.scenes:
        assert scene.shots, "chaque étape doit porter un plan"


def test_every_shot_fits_the_5s_horizon_after_split():
    """Le service garantit qu'aucun plan ne dépasse l'horizon i2v (5 s)."""
    horizon = max_coherent_duration_s(VIDEO_MODEL)
    assert horizon == 5.0  # le « 5 sec max » de la demande
    plan = generate_system_plan(_IMG, hint="un circuit imprimé", n_steps=4)
    for scene in plan.scenes:
        for shot in scene.shots:
            assert shot.duree_s <= horizon


def test_narration_fr_and_visual_en_present():
    """Narration FR (parlée) + sujet visuel EN (prompt image) sur chaque étape."""
    plan = FakeSystemExplainer().explain_system(_IMG, n_steps=2)
    for scene in plan.scenes:
        shot = scene.shots[0]
        assert shot.narration_fr.strip(), "narration FR attendue"
        assert shot.sujet.strip() or shot.start_image.strip(), "sujet/visuel EN attendu"


def test_builds_valid_document_on_the_common_rail():
    """image → VideoPlan → EditorDocument, chaque brique prête, et le spec compile."""
    plan = generate_system_plan(_IMG, hint="une foule qui s'organise", n_steps=3)
    doc = scene_plan_to_document(plan, title="Système")
    assert isinstance(doc, EditorDocument)
    assert doc.bricks
    for brick in doc.bricks:
        if isinstance(brick, ClipBrick):
            assert validate_clip(brick) == {}, f"brique non prête : {validate_clip(brick)}"
    spec = document_to_spec(doc)  # invariant fort : le rendu compile sans lever
    assert spec.segments


def test_dispatch_requires_an_image():
    """Le format 'systeme' refuse une entrée sans image (garde-fou clair)."""
    with pytest.raises(ValueError, match="image"):
        build_format_document("systeme", "explique", openai_key=None, options={})
