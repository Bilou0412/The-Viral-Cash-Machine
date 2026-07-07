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


def test_video_shots_seed_from_scene_env_photo():
    """E2 : chaque plan anime SA frame, composée avec la photo d'ENV en référence."""
    plan = FakeSceneDecomposer().decompose_video("x", n_scenes=1)
    doc = scene_plan_to_document(plan)
    scene = doc.scenes[0]
    env_ref = f"{{brick:{scene.environment_photo_ref}.image}}"
    videos = [b for b in doc.bricks if getattr(b, "kind", None) == "video"]
    assert videos, "au moins un plan vidéo"
    for v in videos:
        assert v.motion is not None
        assert v.motion.params.get("image") == f"{{brick:{v.id}.image}}"  # anime SA frame
        assert v.image.params.get("image_input") == env_ref              # ancrée à l'établissement


# -- Décrypteur OpenAI (Phase 3) — testé avec un CLIENT STUB (aucun réseau) -----

class _Msg:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, scripted: list[str]) -> None:
        self._scripted = scripted
        self._i = 0

    def create(self, **_kw: object) -> _Resp:
        content = self._scripted[min(self._i, len(self._scripted) - 1)]
        self._i += 1
        return _Resp(content)


class _Chat:
    def __init__(self, scripted: list[str]) -> None:
        self.completions = _Completions(scripted)


class _StubClient:
    def __init__(self, scripted: list[str]) -> None:
        self.chat = _Chat(scripted)


def test_openai_scene_decomposer_two_phase_stub():
    from src.features.scenes.openai_scene_decomposer import OpenAISceneDecomposer

    macro = (
        '{"scenes":[{"id":"s1","title":"Intro","environment_desc":'
        '"a dark abandoned subway tunnel","intention":"on entre dans le noir"}]}'
    )
    micro = (
        '{"shots":[{"id":"s1_a","kind":"video","visual_desc":"detail of the rails",'
        '"motion_desc":"slow push in","narration_fr":"On avance.","duration_s":3}]}'
    )
    dec = OpenAISceneDecomposer(_StubClient([macro, micro]), "gpt-x")
    plan = dec.decompose_video("un thriller vertical", style_identity="cold tones", n_scenes=1)
    assert len(plan.scenes) == 1
    sc = plan.scenes[0]
    assert sc.environment_desc == "a dark abandoned subway tunnel"
    assert len(sc.shots) == 1
    assert sc.shots[0].kind == "video"
    assert sc.shots[0].narration_fr == "On avance."
