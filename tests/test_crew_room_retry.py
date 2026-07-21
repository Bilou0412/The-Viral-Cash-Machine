"""Robustesse de la table ronde OpenAI : un appel d'agent qui échoue est RETENTÉ.

Régression du 502 sur `POST /documents/{id}/scenes/next` : une scène = 9 appels
OpenAI séquentiels (1 contrat + 4 départements + 4 révisions) ; un seul échec
transitoire (JSON malformé, reset réseau, 5xx) faisait planter toute la scène.
Le contrat/brouillon est désormais retenté (`_retry`, `_MAX_ATTEMPTS`). Offline :
un faux client OpenAI scripté (aucun réseau), `time.sleep` neutralisé.
"""

import types

import pytest

pytest.importorskip("pydantic")

from src.features.brief.model import Brief
from src.features.crew_room.model import RoomMemory, SceneBrief
from src.features.crew_room.openai_room import _MAX_ATTEMPTS, OpenAIContractAgent
from src.features.crew_room.ports import CrewAgentError

_VALID_CONTRACT = '{"env_intention":"a quiet room","shots":[{"id":"s1_sh1","beat":"intro","kind":"video"}]}'


class _Completions:
    """Rejoue un script d'items : une Exception est levée, une str est renvoyée."""

    def __init__(self, script: list[object]) -> None:
        self._script = script
        self.calls = 0

    def create(self, **_kw: object) -> object:
        item = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=item))]
        )


def _fake_client(script: list[object]) -> tuple[object, _Completions]:
    comp = _Completions(script)
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=comp))
    return client, comp


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr("src.features.crew_room.openai_room.time.sleep", lambda _s: None)


def _define(client: object):
    return OpenAIContractAgent(client, "m").define(  # type: ignore[arg-type]
        brief=Brief(), scene_brief=SceneBrief(id="s1", title="Intro"), memory=RoomMemory()
    )


def test_contract_retries_then_succeeds():
    """1er appel casse (reset réseau), le 2e renvoie un contrat valide → succès."""
    client, comp = _fake_client([RuntimeError("connection reset"), _VALID_CONTRACT])
    contract = _define(client)
    assert len(contract.shots) == 1
    assert comp.calls == 2  # a bien retenté une fois


def test_contract_recovers_from_malformed_json():
    """JSON illisible d'abord, puis valide → le parse aussi est retenté."""
    client, comp = _fake_client(["not json at all", _VALID_CONTRACT])
    contract = _define(client)
    assert contract.shots
    assert comp.calls == 2


def test_contract_gives_up_after_max_attempts():
    """Échec persistant → CrewAgentError après _MAX_ATTEMPTS tentatives (502 propre)."""
    client, comp = _fake_client(["still not json"])
    with pytest.raises(CrewAgentError):
        _define(client)
    assert comp.calls == _MAX_ATTEMPTS
