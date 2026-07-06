"""Lot DA — le directeur artistique : agent + application au document (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick
from src.features.brief.model import Brief
from src.features.crew import CrewAgentError, SceneRef
from src.features.crew.fake_art_direction_agent import FakeArtDirectionAgent
from src.features.crew.openai_art_direction_agent import OpenAIArtDirectionAgent
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.studio.api.services.art_direction import direct_art_direction


def _sample_doc():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    return scene_plan_to_document(plan, title="Ma vidéo")


# -- agent DA FAKE ------------------------------------------------------------

def test_fake_art_direction_rewrites_and_is_deterministic():
    scenes = [SceneRef(id="s1", title="T", environment="dark subway platform")]
    a = FakeArtDirectionAgent()
    r1 = a.direct(tone="horreur", platform="tiktok", language="fr", art_direction="", scenes=scenes)
    r2 = a.direct(tone="horreur", platform="tiktok", language="fr", art_direction="", scenes=scenes)
    assert r1.model_dump() == r2.model_dump()
    assert r1.art_direction  # style commun posé
    assert r1.scenes[0].scene_id == "s1"
    assert "dark subway platform" in r1.scenes[0].environment_prompt  # décor gardé
    assert r1.scenes[0].environment_prompt != "dark subway platform"  # mais enrichi


# -- agent DA OpenAI : client STUB (aucun réseau) -----------------------------

class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, content):
        self._content = content

    def create(self, **_kw):
        return _Resp(self._content)


class _Chat:
    def __init__(self, content):
        self.completions = _Completions(content)


class _StubClient:
    def __init__(self, content):
        self.chat = _Chat(content)


def test_openai_art_direction_parses():
    payload = (
        '{"art_direction":"cold teal grade, hard shadows","scenes":['
        '{"scene_id":"s1","environment_prompt":"a cold abandoned subway, teal grade"}]}'
    )
    out = OpenAIArtDirectionAgent(_StubClient(payload), "gpt-x").direct(
        tone="x", platform="tiktok", language="fr", art_direction="",
        scenes=[SceneRef(id="s1", title="T", environment="subway")],
    )
    assert out.art_direction and out.scenes[0].scene_id == "s1"


def test_openai_art_direction_empty_raises():
    ag = OpenAIArtDirectionAgent(_StubClient('{"art_direction":"x","scenes":[]}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        ag.direct(tone="x", platform="tiktok", language="fr", art_direction="", scenes=[])


# -- service : applique au document, revalide ---------------------------------

def test_direct_art_direction_mutates_env_bricks_and_stays_valid():
    doc = _sample_doc()
    # Prompts d'environnement avant.
    before = {
        s.environment_photo_ref: dict(_env_brick(doc, s.environment_photo_ref).image.params)
        for s in doc.scenes
    }
    out = direct_art_direction(doc, Brief(ton="sombre"))  # Fake (pas de clé)

    assert out.global_context.art_direction  # art direction globale posée
    for scene in out.scenes:
        env = _env_brick(out, scene.environment_photo_ref)
        assert env.image.params["prompt"] != before[scene.environment_photo_ref]["prompt"]
        # Reste générable (invariant du rail : prêt ⟹ compile réussit).
        assert validate_clip(env) == {}


def _env_brick(doc, brick_id: str) -> ClipBrick:
    b = next(b for b in doc.bricks if b.id == brick_id)
    assert isinstance(b, ClipBrick)
    return b
