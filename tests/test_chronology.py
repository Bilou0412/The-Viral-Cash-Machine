"""Tests du mode « chronologie procédurale » (LOT 1.6) — AUCUN réseau.

Deux contrats :
1. Les helpers PURS (résumé courant, réconciliation de longueur, assemblage)
   font ce qu'il faut sur des données simples, sans client ni réseau.
2. L'orchestration `decompose_adventure(..., chronology=...)` :
   - chronology=True assemble un AdventureScript valide via un FAUX client OpenAI
     (stub minimal exposant `.chat.completions.create`), sans réseau ;
   - chronology=False reste STRICTEMENT le chemin historique (un seul appel).

IMPORTANT : ce module n'importe JAMAIS `openai` (absent hors conteneur) — le
faux client est une petite classe locale.
"""

import json

import pytest

pydantic = pytest.importorskip("pydantic")

from src.features.scripting.adventure import (  # noqa: E402
    AdventureScript,
    Choice,
    Round,
    VoiceProfile,
)
from src.features.scripting import openai_adventure_decomposer as DEC  # noqa: E402
from src.features.scripting.openai_adventure_decomposer import (  # noqa: E402
    OpenAIAdventureDecomposer,
    _assemble_script,
    _reconcile_timeline_length,
    _running_summary,
)


# ---------------------------------------------------------------------------
# Fabriques (mêmes valeurs traçables que tests/test_adventure.py)
# ---------------------------------------------------------------------------

def _round(n: int, fatal_first: bool = True) -> Round:
    return Round(
        action_desc=f"climbs down a broken ladder into level {n}",
        action_narration_fr=f"Il s'enfonce vers le niveau {n}.",
        environment_desc=f"a flooded mine shaft on level {n}",
        danger_desc=f"loose slabs hanging over the path on level {n}",
        environment_narration_fr=f"Tout craque au niveau {n}.",
        character_line_fr=f"On descend encore, niveau {n} ?",
        character_delivery="whispering",
        choices=(
            Choice(label_fr="Sauter", image_desc=f"a leap over a black pit on level {n}", is_fatal=fatal_first),
            Choice(label_fr="Ramper", image_desc=f"crawling under low rock on level {n}", is_fatal=not fatal_first),
        ),
        choice_narration_fr=f"Sauter, ou ramper, niveau {n} ?",
        fatal_kill_desc=f"drags you under the water of level {n}",
        fatal_pov_reaction=f"you thrash and your scream drowns on level {n}",
        fatal_narration_fr=f"Si tu as sauté au niveau {n}...",
        survival_outcome_desc=f"you pull yourself onto dry stone past level {n}",
        survival_narration_fr=f"Tu survis au niveau {n}.",
    )


def _intro_parts() -> dict:
    """Toutes les clés non-`rounds` d'un AdventureScript, en dict (comme le LLM)."""
    return {
        "char_left_name": "Étienne",
        "char_right_name": "Mathilde",
        "char_left_desc": "a tall gaunt man in a soaked miner's coat",
        "char_right_desc": "a wiry woman with a cracked lantern",
        "char_left_voice": {"description": "a young hoarse whispering male voice"},
        "char_right_voice": {"description": "a low steady breathy female voice"},
        "char_left_personality_fr": "Un mineur calme qui connaît la galerie.",
        "char_right_personality_fr": "Une femme pressée, prête à tout.",
        "char_left_intro_line_fr": "Reste près de moi dans le noir.",
        "char_right_intro_line_fr": "Vite, il faut descendre.",
        "transition_narration_fr": "Si tu as choisi Étienne...",
        "epilogue_other_desc": "walking a parallel corridor, fading into darkness",
        "epilogue_narration_fr": "Si tu avais choisi l'autre...",
    }


# ---------------------------------------------------------------------------
# Faux client OpenAI minimal (aucun réseau, aucun import openai)
# ---------------------------------------------------------------------------

class _Msg:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, owner: "_FakeClient"):
        self._owner = owner

    def create(self, *, model, response_format, messages):  # noqa: ANN001
        self._owner.calls.append(messages)
        content = self._owner.responses[self._owner.index]
        self._owner.index += 1
        return _Resp(content)


class _Chat:
    def __init__(self, owner: "_FakeClient"):
        self.completions = _Completions(owner)


class _FakeClient:
    """Renvoie `responses[i]` (str JSON) au i-ème appel `.chat.completions.create`."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.index = 0
        self.calls = []
        self.chat = _Chat(self)


# ---------------------------------------------------------------------------
# 1. Helpers PURS
# ---------------------------------------------------------------------------

def test_running_summary_vide_au_depart():
    s = _running_summary([])
    assert isinstance(s, str) and s.strip()
    assert "premier round" in s


def test_running_summary_mentionne_les_issues_et_grandit():
    one = _running_summary([_round(1)])
    two = _running_summary([_round(1), _round(2, fatal_first=False)])
    assert one.strip() and two.strip()
    # mentionne l'issue de survie d'un round précédent
    assert "Tu survis au niveau 1." in one
    assert _round(1).survival_outcome_desc in one
    # grandit avec plus de rounds
    assert len(two) > len(one)
    assert "Round 2" in two


def test_reconcile_timeline_tronque_et_complete():
    # trop long → tronqué à N
    assert _reconcile_timeline_length(("a", "b", "c", "d"), 2) == ("a", "b")
    # trop court → complété à N
    out = _reconcile_timeline_length(("a",), 3)
    assert len(out) == 3
    assert out[0] == "a"
    assert all(b.strip() for b in out)
    # juste bon → inchangé
    assert _reconcile_timeline_length(("a", "b"), 2) == ("a", "b")


def test_assemble_script_depuis_parties():
    rounds = [_round(i, fatal_first=(i % 2 == 1)) for i in range(1, 5)]
    s = _assemble_script(_intro_parts(), rounds)
    assert isinstance(s, AdventureScript)
    assert len(s.rounds) == 4
    assert s.char_left_name == "Étienne"
    assert s.char_left_voice == VoiceProfile(
        description="a young hoarse whispering male voice"
    )


# ---------------------------------------------------------------------------
# 2. Orchestration chronology=True via faux client (aucun réseau)
# ---------------------------------------------------------------------------

def test_decompose_chronology_assemble_un_script_valide():
    n = 3
    timeline_json = json.dumps(
        {"beats": [f"Beat {i}" for i in range(1, n + 1)]}
    )
    rounds_json = [_round(i).model_dump_json() for i in range(1, n + 1)]
    intro_json = json.dumps(_intro_parts())
    # ordre des appels : 1 timeline, N rounds, 1 intro/épilogue
    responses = [timeline_json, *rounds_json, intro_json]

    client = _FakeClient(responses)
    dec = OpenAIAdventureDecomposer(client, "fake-model")  # type: ignore[arg-type]
    s = dec.decompose_adventure(
        "mine hantée", "Étienne", "Mathilde", n_rounds=n, chronology=True
    )

    assert isinstance(s, AdventureScript)
    assert len(s.rounds) == n
    # 1 (timeline) + n (rounds) + 1 (intro) appels
    assert len(client.calls) == n + 2


def test_chronology_timeline_mauvaise_longueur_est_reconciliee():
    """Une timeline trop courte ne casse pas : reconciliation + génération complète."""
    n = 3
    timeline_json = json.dumps({"beats": ["seul beat"]})  # 1 au lieu de 3
    rounds_json = [_round(i).model_dump_json() for i in range(1, n + 1)]
    intro_json = json.dumps(_intro_parts())
    responses = [timeline_json, *rounds_json, intro_json]

    client = _FakeClient(responses)
    dec = OpenAIAdventureDecomposer(client, "fake-model")  # type: ignore[arg-type]
    s = dec.decompose_adventure(
        "mine hantée", "Étienne", "Mathilde", n_rounds=n, chronology=True
    )
    assert len(s.rounds) == n


# ---------------------------------------------------------------------------
# 3. Chemin par DÉFAUT inchangé (un seul appel)
# ---------------------------------------------------------------------------

def test_default_path_inchange_un_seul_appel():
    """chronology=False : exactement le chemin historique (un appel, script parsé)."""
    s_ref = _assemble_script(
        _intro_parts(), [_round(1), _round(2, fatal_first=False), _round(3)]
    )
    client = _FakeClient([s_ref.model_dump_json()])
    dec = OpenAIAdventureDecomposer(client, "fake-model")  # type: ignore[arg-type]
    s = dec.decompose_adventure(
        "mine hantée", "Étienne", "Mathilde", n_rounds=3, chronology=False
    )
    assert isinstance(s, AdventureScript)
    assert s == s_ref
    assert len(client.calls) == 1  # un seul appel, pas la boucle chronology


def test_default_path_quand_flag_absent(monkeypatch):
    """Sans arg et sans env : défaut = chemin historique (un seul appel)."""
    monkeypatch.delenv(DEC._CHRONOLOGY_ENV, raising=False)
    s_ref = _assemble_script(_intro_parts(), [_round(1)])
    client = _FakeClient([s_ref.model_dump_json()])
    dec = OpenAIAdventureDecomposer(client, "fake-model")  # type: ignore[arg-type]
    s = dec.decompose_adventure("x", "Étienne", "Mathilde", n_rounds=1)
    assert s == s_ref
    assert len(client.calls) == 1


def test_env_flag_active_chronology(monkeypatch):
    """VCM_CHRONOLOGY=1 active la chronologie quand l'arg est None."""
    monkeypatch.setenv(DEC._CHRONOLOGY_ENV, "1")
    n = 2
    timeline_json = json.dumps({"beats": [f"Beat {i}" for i in range(1, n + 1)]})
    rounds_json = [_round(i).model_dump_json() for i in range(1, n + 1)]
    intro_json = json.dumps(_intro_parts())
    client = _FakeClient([timeline_json, *rounds_json, intro_json])
    dec = OpenAIAdventureDecomposer(client, "fake-model")  # type: ignore[arg-type]
    s = dec.decompose_adventure("x", "Étienne", "Mathilde", n_rounds=n)
    assert len(s.rounds) == n
    assert len(client.calls) == n + 2  # boucle chronology empruntée
