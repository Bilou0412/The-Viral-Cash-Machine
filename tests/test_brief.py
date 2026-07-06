"""Lot Brief — le producteur (agent de dialogue) + fil brief→décrypteur (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.features.brief import Brief, CrewAgentError, FakeProducerAgent
from src.features.brief.openai_producer_agent import OpenAIProducerAgent
from src.features.crew import CREW
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.features.scenes.openai_scene_decomposer import OpenAISceneDecomposer


def test_roster_has_producteur_first_in_developpement():
    """Le producteur ouvre le casting (phase développement, kind 'brief')."""
    prod = next(r for r in CREW if r.key == "producteur")
    assert prod.phase == "developpement"
    assert prod.kind == "brief"
    assert CREW[0].key == "producteur"  # en amont du scénariste


# -- producteur FAKE : déterministe, l'humain garde la main -------------------

def test_fake_producer_completes_brief():
    b = FakeProducerAgent().draft_brief(idea="Un métro hanté la nuit, horreur")
    assert b.objectif and b.audience and b.plateforme == "tiktok"
    assert b.langue == "fr" and b.ton  # ton dérivé (heuristique horreur)


def test_fake_producer_respects_partial():
    """Les champs déjà décidés par l'humain priment sur la proposition."""
    partial = Brief(plateforme="reels", langue="en", audience="pros B2B")
    b = FakeProducerAgent().draft_brief(idea="un tuto", partial=partial)
    assert b.plateforme == "reels"
    assert b.langue == "en"
    assert b.audience == "pros B2B"
    assert b.objectif  # complété par l'agent (était vide)


def test_fake_producer_deterministic():
    a = FakeProducerAgent()
    assert a.draft_brief(idea="x").model_dump() == a.draft_brief(idea="x").model_dump()


# -- producteur OpenAI : client STUB (aucun réseau) ---------------------------

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
        self.systems: list[str] = []

    def create(self, **kw):
        # Capture le prompt système pour vérifier le fil du Brief.
        for m in kw.get("messages", []):
            if m.get("role") == "system":
                self.systems.append(m["content"])
        return _Resp(self._content)


class _Chat:
    def __init__(self, content):
        self.completions = _Completions(content)


class _StubClient:
    def __init__(self, content):
        self.chat = _Chat(content)


def test_openai_producer_parses_brief():
    payload = (
        '{"objectif":"faire peur","audience":"ados","plateforme":"shorts",'
        '"duree_s":25,"budget_usd":2,"ton":"angoissant","langue":"fr","notes":""}'
    )
    b = OpenAIProducerAgent(_StubClient(payload), "gpt-x").draft_brief(idea="métro")
    assert b.objectif == "faire peur"
    assert b.plateforme == "shorts"
    assert b.duree_s == 25


def test_openai_producer_empty_raises():
    ag = OpenAIProducerAgent(_StubClient('{"objectif":""}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        ag.draft_brief(idea="x")


# -- fil Brief → décrypteur ---------------------------------------------------

# Un seul payload sert les deux phases (extra='ignore' → chaque phase lit sa clé).
_SCENE_SHOT = (
    '{"scenes":[{"id":"s1","title":"T","environment_desc":"env","intention":"i"}],'
    '"shots":[{"id":"s1_sh1","kind":"video","visual_desc":"v","motion_desc":"m",'
    '"narration_fr":"n","duration_s":3}]}'
)


def test_decomposer_defaults_are_french_no_budget():
    """Défauts (pas de brief) : narration FRANÇAISE, pas de budget-temps imposé."""
    stub = _StubClient(_SCENE_SHOT)
    OpenAISceneDecomposer(stub, "gpt-x").decompose_video("idée", n_scenes=1)
    joined = "\n".join(stub.chat.completions.systems)
    assert "FRENCH" in joined
    assert "budget" not in joined.lower()  # aucune durée cible → pas de consigne budget


def test_decomposer_honors_brief_language_and_duration():
    """`language='en'` → libellés EN ; `target_duration_s>0` → budget-temps par scène."""
    stub = _StubClient(_SCENE_SHOT)
    OpenAISceneDecomposer(stub, "gpt-x").decompose_video(
        "idea", n_scenes=1, platform="reels", language="en", target_duration_s=30
    )
    systems = stub.chat.completions.systems
    macro, micro = systems[0], systems[1]
    assert "ENGLISH" in macro and "for Reels" in macro
    assert "ENGLISH" in micro  # narration EN
    assert "about 30s" in micro  # 30s / 1 scène


def test_fake_decomposer_ignores_brief_params():
    """Le Fake accepte les nouveaux kwargs et reste déterministe (golden scènes)."""
    dec = FakeSceneDecomposer()
    a = dec.decompose_video("x", n_scenes=2)
    b = dec.decompose_video("x", n_scenes=2, platform="reels", language="en", target_duration_s=99)
    assert a.model_dump() == b.model_dump()
