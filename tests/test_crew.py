"""L1 — l'équipe d'agents-métiers : l'attaché de presse / Growth (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.features.crew import CREW, PHASES, CrewAgentError
from src.features.crew.fake_distribution_agent import FakeDistributionAgent
from src.features.crew.openai_distribution_agent import OpenAIDistributionAgent


def test_roster_covers_every_phase():
    """Chaque phase du studio a au moins un métier dans le casting."""
    phases_in_crew = {r.phase for r in CREW}
    assert set(PHASES) == phases_in_crew
    assert any(r.kind == "distribution" for r in CREW)  # l'attaché de presse existe


def test_fake_distribution_agent_deterministic():
    a = FakeDistributionAgent()
    k1 = a.write_kit(title="Le métro hanté", synopsis="deux amis", narration="Attends…")
    k2 = a.write_kit(title="Le métro hanté", synopsis="deux amis", narration="Attends…")
    assert k1.model_dump() == k2.model_dump()
    assert k1.title and k1.hashtags and k1.hook


# -- attaché de presse OpenAI : client STUB (aucun réseau) --------------------

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


def test_openai_distribution_agent_parses_kit():
    payload = (
        '{"title":"Le métro hanté 😱","description":"Une descente dans le noir.",'
        '"hashtags":["#fyp","#horreur"],"hook":"Personne n\'en est ressorti."}'
    )
    ag = OpenAIDistributionAgent(_StubClient(payload), "gpt-x")
    kit = ag.write_kit(title="Le métro hanté", synopsis="x", narration="")
    assert kit.title.startswith("Le métro hanté")
    assert kit.hashtags == ["#fyp", "#horreur"]
    assert kit.hook


def test_openai_distribution_agent_empty_raises():
    ag = OpenAIDistributionAgent(_StubClient('{"title":""}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        ag.write_kit(title="x", synopsis="y", narration="")
