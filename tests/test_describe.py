"""Descripteur TEXTE complet + robustesse des ids dupliqués (bug trouvé en test réel)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.describe import describe_document
from src.editor.document import ClipBrick
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.features.scenes.model import ScenePlan, ShotCharacterPlan, ShotPlan, VideoPlan


def test_describe_renders_the_whole_video_as_text():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=1)
    doc = scene_plan_to_document(plan)
    text = describe_document(doc)
    # les grandes sections sont présentes
    for marker in ("VIDÉO —", "DÉCORS (bible)", "PERSONNAGES (bible)", "SCÈNE", "ÉTABLISSEMENT",
                   "PLAN", "IMAGE ▸", "MOUVEMT", "VOIX", "Léa"):
        assert marker in text, f"section manquante : {marker}"
    assert text.endswith("\n")


def test_duplicate_ids_across_scenes_are_made_unique():
    """Régression : le décrypteur LLM renvoie parfois des ids scène/plan RÉPÉTÉS
    (« scene_1 »/« shot_1 » partout) → le doc doit quand même être valide (ids uniques)."""
    def _scene() -> ScenePlan:  # MÊMES ids à chaque appel
        return ScenePlan(
            id="scene_1", title="S", environment_desc="a room", location_ref="loc",
            shots=[ShotPlan(id="shot_1", kind="video", duree_s=3.0,
                            personnages=[ShotCharacterPlan(name="Léa")])],
        )

    plan = VideoPlan(title="T", scenes=[_scene(), _scene(), _scene()])
    doc = scene_plan_to_document(plan)   # ne doit PAS lever (ids dédupliqués)
    brick_ids = [b.id for b in doc.bricks]
    scene_ids = [s.id for s in doc.scenes]
    assert len(brick_ids) == len(set(brick_ids))   # briques uniques
    assert len(scene_ids) == len(set(scene_ids))   # scènes uniques
    assert len([b for b in doc.bricks if isinstance(b, ClipBrick) and b.shot]) == 3  # 3 plans


def test_role_names_lose_their_french_article():
    """« Le livreur » (rôle articulé du LLM) → l'article FR ne fuit pas dans le prompt EN."""
    from src.editor.compile_shot import compile_image_prompt, resolve_shot
    plan = VideoPlan(title="T", scenes=[ScenePlan(
        id="s1", environment_desc="a desk", location_ref="loc",
        shots=[ShotPlan(id="sh1", kind="video", duree_s=3.0,
                        personnages=[ShotCharacterPlan(name="Le livreur", action="opens a box")])],
    )])
    doc = scene_plan_to_document(plan)
    assert doc.bible and doc.bible[0].name == "livreur"      # article de tête retiré
    scene_of = {sid: sc for sc in doc.scenes for sid in sc.shot_ids}
    clip = next(b for b in doc.bricks if isinstance(b, ClipBrick) and b.shot)
    img = compile_image_prompt(resolve_shot(doc, scene_of[clip.id], clip.shot))
    assert "Le livreur" not in img                          # plus d'article FR


def test_describe_shows_per_plan_intention():
    plan = VideoPlan(title="T", scenes=[ScenePlan(
        id="s1", environment_desc="x", location_ref="loc",
        shots=[ShotPlan(id="sh1", kind="video", duree_s=3.0,
                        intention_plan="montrer l'hésitation avant le geste")],
    )])
    doc = scene_plan_to_document(plan)
    assert "montrer l'hésitation avant le geste" in describe_document(doc)
