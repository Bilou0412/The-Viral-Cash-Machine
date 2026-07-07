"""Lot G1 — la table ronde : moteur + mémoire séquentielle (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick, EditorDocument
from src.features.brief.model import Brief
from src.features.crew_room import (
    ROOM_VOICES,
    FakeRoomVoice,
    FakeSceneSynthesizer,
    RoomMemory,
    SceneBrief,
    run_scene_room,
)
from src.features.crew_room.openai_room import OpenAIRoomVoice, OpenAISceneSynthesizer
from src.features.crew_room.ports import CrewAgentError
from src.features.scenes import scene_plan_to_document
from src.studio.api.services.room import build_next_scene, plan_room_state


def _brief() -> Brief:
    return Brief(objectif="faire peur", audience="ados", ton="sombre")


def _sb(sid: str = "s1") -> SceneBrief:
    return SceneBrief(id=sid, title="Le quai désert", intention="installer le malaise",
                      environment="empty subway platform at 2am")


# -- moteur (Fake) : débat déterministe → scène structurée --------------------

def test_run_scene_room_deterministic_multiturn():
    r1 = run_scene_room(_brief(), _sb(), RoomMemory(), voices=FakeRoomVoice(),
                        synthesizer=FakeSceneSynthesizer(), rounds=2)
    r2 = run_scene_room(_brief(), _sb(), RoomMemory(), voices=FakeRoomVoice(),
                        synthesizer=FakeSceneSynthesizer(), rounds=2)
    assert r1.model_dump() == r2.model_dump()  # déterministe
    assert len(r1.transcript) == len(ROOM_VOICES) * 2  # 2 tours × 5 voix
    assert r1.transcript[0].role == "realisateur"  # le réalisateur ouvre
    assert r1.new_characters and r1.new_characters[0].name == "Léa"
    assert r1.scene.shots and all(s.characters for s in r1.scene.shots)


def test_room_scene_compiles_to_ready_bricks():
    from src.features.scenes.model import VideoPlan

    res = run_scene_room(_brief(), _sb(), RoomMemory(), voices=FakeRoomVoice(),
                         synthesizer=FakeSceneSynthesizer(), rounds=1)
    doc = scene_plan_to_document(VideoPlan(scenes=[res.scene], cast=res.new_characters))
    for b in doc.bricks:
        if isinstance(b, ClipBrick):
            assert validate_clip(b) == {}  # scène prête à générer


# -- mémoire séquentielle : la bible s'accumule, pas de doublon ---------------

def test_sequential_memory_accumulates_bible_once():
    from src.features.scenes.model import ScenePlan

    arc = [ScenePlan(id=f"s{i}", title=f"Scène {i}", environment_desc=f"lieu {i}",
                     context_text=f"beat {i}") for i in (1, 2, 3)]
    state = plan_room_state(arc)
    doc = EditorDocument(title="V")
    for _ in range(3):
        build_next_scene(doc, state, _brief())
    assert state.built == ["s1", "s2", "s3"]
    assert [c.name for c in state.memory.bible] == ["Léa"]  # introduite 1×, réutilisée
    assert len(state.transcripts) == 3
    assert "Scène 1" in state.memory.synopsis_so_far and "Scène 3" in state.memory.synopsis_so_far
    assert len(doc.scenes) == 3
    for b in doc.bricks:
        if isinstance(b, ClipBrick):
            assert validate_clip(b) == {}


# -- voix / synthèse OpenAI : client STUB -------------------------------------

class _Msg:
    def __init__(self, content): self.content = content
class _Choice:
    def __init__(self, content): self.message = _Msg(content)
class _Resp:
    def __init__(self, content): self.choices = [_Choice(content)]
class _Completions:
    def __init__(self, content): self._c = content
    def create(self, **_kw): return _Resp(self._c)
class _Chat:
    def __init__(self, content): self.completions = _Completions(content)
class _Stub:
    def __init__(self, content): self.chat = _Chat(content)


def test_openai_voice_returns_message():
    v = OpenAIRoomVoice(_Stub("Décor : quai sombre, néons qui grésillent."), "gpt-x")
    msg = v.speak(role="directeur_artistique", brief=_brief(), scene_brief=_sb(),
                  memory=RoomMemory(), transcript=[])
    assert "quai sombre" in msg


def test_openai_synth_parses_scene():
    payload = (
        '{"environment_desc":"dark platform","lighting":"cold","shots":['
        '{"id":"s1_sh1","kind":"video","framing":"wide","decor":"platform",'
        '"lighting":"cold","narration_fr":"La nuit tombe.","characters":['
        '{"name":"Léa","appearance":"teen","wardrobe":"coat","expression":"tense","action":"waits"}]}],'
        '"new_characters":[{"name":"Léa","appearance":"teen","wardrobe":"coat"}]}'
    )
    synth = OpenAISceneSynthesizer(_Stub(payload), "gpt-x")
    res = synth.synthesize(brief=_brief(), scene_brief=_sb(), memory=RoomMemory(), transcript=[])
    assert res.scene.shots[0].framing == "wide"
    assert res.scene.shots[0].characters[0].name == "Léa"
    assert res.new_characters[0].name == "Léa"


def test_openai_synth_empty_raises():
    synth = OpenAISceneSynthesizer(_Stub('{"shots":[]}'), "gpt-x")
    with pytest.raises(CrewAgentError):
        synth.synthesize(brief=_brief(), scene_brief=_sb(), memory=RoomMemory(), transcript=[])
