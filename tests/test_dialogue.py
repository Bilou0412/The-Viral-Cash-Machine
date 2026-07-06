"""Lot Dialoguiste — agent + application au document (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick
from src.features.brief.model import Brief
from src.features.crew import CrewAgentError, NarrationRef
from src.features.crew.fake_dialogue_agent import FakeDialogueAgent
from src.features.crew.openai_dialogue_agent import OpenAIDialogueAgent
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.studio.api.services.dialogue import direct_dialogue


def _sample_doc():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    return scene_plan_to_document(plan, title="Ma vidéo")


def _texts(doc):
    return {
        child.id: child.params.get("text")
        for b in doc.bricks
        if isinstance(b, ClipBrick)
        for child in b.children
    }


# -- dialoguiste FAKE ---------------------------------------------------------

def test_fake_dialogue_polishes_keeps_ids_deterministic():
    lines = [NarrationRef(id="c1", text="la tension monte"), NarrationRef(id="c2", text="fin")]
    a = FakeDialogueAgent()
    r1 = a.write_dialogue(tone="", audience="", language="fr", characters={}, lines=lines)
    r2 = a.write_dialogue(tone="", audience="", language="fr", characters={}, lines=lines)
    assert r1.model_dump() == r2.model_dump()
    assert [line.line_id for line in r1.lines] == ["c1", "c2"]  # ids gardés
    assert r1.lines[0].text == "La tension monte."  # majuscule + ponctuation
    assert r1.lines[1].text == "Fin."


# -- dialoguiste OpenAI : client STUB -----------------------------------------

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


def test_openai_dialogue_parses():
    payload = '{"lines":[{"line_id":"c1","text":"Personne n\'en revient."}]}'
    out = OpenAIDialogueAgent(_StubClient(payload), "gpt-x").write_dialogue(
        tone="x", audience="ados", language="fr", characters={},
        lines=[NarrationRef(id="c1", text="original")],
    )
    assert out.lines[0].line_id == "c1" and out.lines[0].text


def test_openai_dialogue_empty_raises():
    ag = OpenAIDialogueAgent(_StubClient('{"lines":[]}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        ag.write_dialogue(tone="x", audience="", language="fr", characters={}, lines=[])


# -- service : applique au document par id, revalide --------------------------

def test_direct_dialogue_rewrites_children_by_id_and_stays_valid():
    doc = _sample_doc()
    before = _texts(doc)
    assert before  # le Fake décrypteur pose des narrations

    out = direct_dialogue(doc, Brief(ton="sombre", audience="ados"))  # Fake

    after = _texts(out)
    assert set(after) == set(before)  # mêmes enfants (aucun perdu/ajouté)
    assert all(v for v in after.values())  # tous non vides
    # Toutes les briques restent générables (invariant du rail).
    for b in out.bricks:
        if isinstance(b, ClipBrick):
            assert validate_clip(b) == {}
