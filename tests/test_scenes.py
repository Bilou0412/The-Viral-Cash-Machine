"""Phase 1 — décrypteur de scènes Fake + builder vers document. Pur, hors-ligne."""

import pytest

pytest.importorskip("pydantic")

from src.editor import document_to_spec
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer


def test_fake_decomposer_deterministic():
    d = FakeSceneDecomposer()
    a = d.decompose_video("idée", n_scenes=2)
    b = d.decompose_video("idée", n_scenes=2)
    assert a.model_dump() == b.model_dump()
    assert len(a.scenes) == 2
    assert all(len(s.shots) == 2 for s in a.scenes)


def test_builder_produces_scene_indexed_document():
    plan = FakeSceneDecomposer().decompose_video("x", n_scenes=2)
    doc = scene_plan_to_document(plan, title="T")
    assert doc.title == "T"
    assert len(doc.scenes) == 2
    # chaque scène = 1 photo d'env + 2 plans = 3 briques ; 2 scènes = 6 briques.
    assert len(doc.bricks) == 6
    known = {b.id for b in doc.bricks}
    for scene in doc.scenes:
        assert scene.environment_photo_ref == scene.shot_ids[0]  # photo d'env en tête
        assert all(sid in known for sid in scene.shot_ids)
    # placement chronologique (briques courtes enchaînées).
    starts = [b.placement.start for b in doc.bricks]
    assert starts == sorted(starts)


def test_built_document_compiles_to_valid_videospec():
    """Le doc scéné compile en VideoSpec (photo d'env = still, plans = footage)."""
    plan = FakeSceneDecomposer().decompose_video("x", n_scenes=2)
    spec = document_to_spec(scene_plan_to_document(plan))
    assert len(spec.segments) == 6  # 2 photos d'env + 4 plans vidéo
