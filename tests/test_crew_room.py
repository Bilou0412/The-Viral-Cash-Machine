"""L'atelier : contrat → brouillons parallèles → mise en commun → révision (offline)."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.document import ClipBrick, EditorDocument
from src.features.brief.model import Brief
from src.features.crew_room import (
    DEPARTMENTS,
    Draft,
    FakeContractAgent,
    FakeDrafter,
    RoomMemory,
    SceneBrief,
    merge_drafts,
    run_scene_room,
)
from src.features.crew_room.openai_room import OpenAIContractAgent, OpenAIDrafter
from src.features.crew_room.ports import CrewAgentError, field_owner
from src.studio.api.services.room import build_next_scene, plan_room_state


def _brief() -> Brief:
    return Brief(objectif="faire peur", audience="ados", ton="sombre")


def _sb(sid: str = "s1") -> SceneBrief:
    return SceneBrief(id=sid, title="Le quai désert", intention="installer le malaise",
                      environment="empty subway platform at 2am")


# -- contrat + brouillons : chacun ne remplit QUE ses champs -------------------

def test_contract_is_deterministic():
    c1 = FakeContractAgent().define(brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    c2 = FakeContractAgent().define(brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    assert c1.model_dump() == c2.model_dump()
    assert [s.id for s in c1.shots] == ["s1_sh1", "s1_sh2"]


def test_each_department_fills_only_its_fields():
    contract = FakeContractAgent().define(brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    d = FakeDrafter()
    da = d.fill(department="directeur_artistique", contract=contract, brief=_brief(),
                scene_brief=_sb(), memory=RoomMemory())
    dop = d.fill(department="chef_operateur", contract=contract, brief=_brief(),
                 scene_brief=_sb(), memory=RoomMemory())
    cast = d.fill(department="casting", contract=contract, brief=_brief(),
                  scene_brief=_sb(), memory=RoomMemory())
    # Le DA remplit décor/lumière, PAS le cadrage.
    assert all("decor" in v and "framing" not in v for v in da.shots.values())
    assert all("framing" in v and "decor" not in v for v in dop.shots.values())
    assert cast.new_characters and cast.shot_characters  # casting = persos
    # Cohérence des propriétaires.
    assert field_owner("decor") == "directeur_artistique"
    assert field_owner("framing") == "chef_operateur"
    assert field_owner("narration") == "dialoguiste"


def test_merge_pulls_each_field_from_its_owner():
    contract = FakeContractAgent().define(brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    d = FakeDrafter()
    drafts = [d.fill(department=dept, contract=contract, brief=_brief(),
                     scene_brief=_sb(), memory=RoomMemory()) for dept in DEPARTMENTS]
    res = merge_drafts(_sb(), contract, drafts)
    shot = res.scene.shots[0]
    assert shot.cadre.taille_plan == "wide shot"   # du chef op → cadre
    assert "subway platform" in shot.start_image   # du DA → décor de la frame
    assert shot.narration_fr                       # du dialoguiste
    assert shot.personnages[0].name == "Léa"       # du casting


# -- moteur : fan-out → merge, déterministe + scène prête ---------------------

def test_run_scene_room_deterministic_and_ready():
    from src.features.scenes import scene_plan_to_document
    from src.features.scenes.model import VideoPlan

    r1 = run_scene_room(_brief(), _sb(), RoomMemory(), director=FakeContractAgent(), drafters=FakeDrafter())
    r2 = run_scene_room(_brief(), _sb(), RoomMemory(), director=FakeContractAgent(), drafters=FakeDrafter())
    assert r1.model_dump() == r2.model_dump()
    # transcript = contrat (réalisateur) + brouillon + révision, un tour/département.
    assert r1.transcript[0].role == "realisateur"
    assert [t.role for t in r1.transcript[1:]] == list(DEPARTMENTS) * 2
    doc = scene_plan_to_document(VideoPlan(scenes=[r1.scene], cast=r1.new_characters))
    for b in doc.bricks:
        if isinstance(b, ClipBrick):
            assert validate_clip(b) == {}


# -- tour de révision (2e passe informée) -------------------------------------

def test_revision_names_character_in_narration():
    kw = {"director": FakeContractAgent(), "drafters": FakeDrafter()}
    blind = run_scene_room(_brief(), _sb(), RoomMemory(), revision_rounds=0, **kw)
    revised = run_scene_room(_brief(), _sb(), RoomMemory(), **kw)  # défaut : 1 tour
    # Sans révision, le dialoguiste écrit à l'aveugle (pas de perso nommé).
    assert "Léa" not in blind.scene.shots[0].narration_fr
    # Avec révision, il VOIT le perso placé par le casting et le nomme.
    assert "Léa" in revised.scene.shots[0].narration_fr
    # revision_rounds=0 ⇒ transcript passe unique (rétro-compat).
    assert [t.role for t in blind.transcript[1:]] == list(DEPARTMENTS)


def test_revise_only_touches_owned_fields():
    contract = FakeContractAgent().define(brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    first = [FakeDrafter().fill(department=d, contract=contract, brief=_brief(),
                                scene_brief=_sb(), memory=RoomMemory()) for d in DEPARTMENTS]
    scene = merge_drafts(_sb(), contract, first).scene
    dia = FakeDrafter().revise(department="dialoguiste", scene=scene, contract=contract,
                               brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    assert all(set(v) == {"narration"} for v in dia.shots.values())  # narration seule
    assert dia.env == {}


def test_sequential_memory_accumulates_bible_once():
    from src.features.scenes.model import ScenePlan

    arc = [ScenePlan(id=f"s{i}", title=f"Scène {i}", environment_desc=f"lieu {i}",
                     intention_scene=f"beat {i}") for i in (1, 2, 3)]
    state = plan_room_state(arc)
    doc = EditorDocument(title="V")
    for _ in range(3):
        build_next_scene(doc, state, _brief())
    assert state.built == ["s1", "s2", "s3"]
    assert [c.name for c in state.memory.bible] == ["Léa"]  # introduite 1×, réutilisée
    assert len(state.transcripts) == 3
    assert len(doc.scenes) == 3


# -- OpenAI (stub) : contrat + brouillon + garde-fous -------------------------

class _Msg:
    def __init__(self, c): self.content = c
class _Choice:
    def __init__(self, c): self.message = _Msg(c)
class _Resp:
    def __init__(self, c): self.choices = [_Choice(c)]
class _Completions:
    def __init__(self, c): self._c = c
    def create(self, **_kw): return _Resp(self._c)
class _Chat:
    def __init__(self, c): self.completions = _Completions(c)
class _Stub:
    def __init__(self, c): self.chat = _Chat(c)


def test_openai_contract_parses():
    payload = '{"env_intention":"dark platform","shots":[{"id":"s1_sh1","beat":"hook","kind":"video"}]}'
    c = OpenAIContractAgent(_Stub(payload), "gpt-x").define(
        brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    assert [s.id for s in c.shots] == ["s1_sh1"]


def test_openai_contract_empty_raises():
    with pytest.raises(CrewAgentError):
        OpenAIContractAgent(_Stub('{"shots":[]}'), "gpt-x").define(
            brief=_brief(), scene_brief=_sb(), memory=RoomMemory())


def test_openai_drafter_parses_owned_fields():
    payload = '{"env":{"decor":"platform","lighting":"cold"},"shots":{"s1_sh1":{"decor":"tiles","lighting":"cold"}}}'
    from src.features.crew_room.model import ContractShot, SceneContract

    contract = SceneContract(shots=[ContractShot(id="s1_sh1", beat="hook")])
    d: Draft = OpenAIDrafter(_Stub(payload), "gpt-x").fill(
        department="directeur_artistique", contract=contract,
        brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    assert d.env["decor"] == "platform"
    assert d.shots["s1_sh1"]["lighting"] == "cold"


def test_openai_drafter_revise_parses_owned_fields():
    from src.features.crew_room.model import ContractShot, SceneContract
    from src.features.scenes.model import ScenePlan, ShotPlan

    payload = '{"shots":{"s1_sh1":{"narration":"Léa hésite."}}}'
    contract = SceneContract(shots=[ContractShot(id="s1_sh1", beat="hook")])
    scene = ScenePlan(id="s1", title="T", shots=[ShotPlan(id="s1_sh1")])
    d: Draft = OpenAIDrafter(_Stub(payload), "gpt-x").revise(
        department="dialoguiste", scene=scene, contract=contract,
        brief=_brief(), scene_brief=_sb(), memory=RoomMemory())
    assert d.shots["s1_sh1"]["narration"] == "Léa hésite."
