"""La « boîte de prod » : superviseur (débat en boucle ciblée) + cap 5 s (offline).

Trois garanties nouvelles, toutes hors-ligne (Fakes) :
1. le superviseur relit et **renvoie corriger** le département incohérent → la boucle
   converge (le perso placé finit nommé dans la narration) ;
2. la boucle **s'arrête** à `max_rounds` (pas de boucle infinie) même si le superviseur
   renvoie toujours corriger ;
3. les plans de la table ronde sont **bornés à 5 s** (scindés, pas rabotés).
"""

import pytest

pytest.importorskip("pydantic")

from src.features.assets.models import VIDEO_MODEL, max_coherent_duration_s
from src.features.brief.model import Brief
from src.features.crew_room import (
    FakeContractAgent,
    FakeDrafter,
    FakeReviewer,
    ReviewVerdict,
    RoomMemory,
    SceneBrief,
    run_scene_room,
)
from src.features.crew_room.model import Draft
from src.features.scenes.model import ScenePlan
from src.studio.api.services.room import build_next_scene, plan_room_state


def _brief() -> Brief:
    return Brief(objectif="faire peur", audience="ados", ton="sombre")


def _sb() -> SceneBrief:
    return SceneBrief(id="s1", title="Le quai", intention="malaise", environment="subway platform")


# 1) Le superviseur fait converger le débat -----------------------------------

def test_supervisor_loop_makes_dialogue_name_the_character():
    """Avec le superviseur (FakeReviewer), le dialoguiste est renvoyé nommer le perso
    placé par le casting → la narration finit par le nommer, et la boucle se clôt."""
    r = run_scene_room(
        _brief(), _sb(), RoomMemory(),
        director=FakeContractAgent(), drafters=FakeDrafter(), reviewer=FakeReviewer(),
    )
    assert "Léa" in r.scene.shots[0].narration_fr
    # le débat est tracé : au moins un verdict du réalisateur + une révision.
    roles = [t.role for t in r.transcript]
    assert roles[0] == "realisateur"
    assert any("révision" in t.role or t.role == "dialoguiste" for t in r.transcript[1:])


# 2) La boucle s'arrête à max_rounds ------------------------------------------

class _AlwaysRedo:
    """Un superviseur têtu : renvoie TOUJOURS corriger → teste le plafond `max_rounds`."""

    def __init__(self) -> None:
        self.calls = 0

    def review(self, *, scene: ScenePlan, contract: object, brief: Brief,
               scene_brief: SceneBrief, memory: RoomMemory) -> ReviewVerdict:
        self.calls += 1
        return ReviewVerdict(ok=False, redo={"dialoguiste": "encore"}, note="jamais content")


def test_supervisor_stops_at_max_rounds():
    rev = _AlwaysRedo()
    r = run_scene_room(
        _brief(), _sb(), RoomMemory(),
        director=FakeContractAgent(), drafters=FakeDrafter(), reviewer=rev, max_rounds=2,
    )
    assert rev.calls == 2          # exactement max_rounds relectures, puis on clôt
    assert r.scene.shots           # une scène est quand même produite


# 3) Cap 5 s : les plans trop longs sont scindés ------------------------------

class _LongDrafter(FakeDrafter):
    """Comme le Fake, mais le chef op impose 6 s (> horizon 5 s) → doit être scindé."""

    def fill(self, *, department, contract, brief, scene_brief, memory) -> Draft:  # type: ignore[no-untyped-def]
        d = super().fill(department=department, contract=contract,
                         brief=brief, scene_brief=scene_brief, memory=memory)
        if department == "chef_operateur":
            return d.model_copy(update={"shots": {k: {**v, "duration": "6"} for k, v in d.shots.items()}})
        return d


def test_crew_room_shots_capped_to_5s():
    horizon = max_coherent_duration_s(VIDEO_MODEL)
    assert horizon == 5.0
    arc = [ScenePlan(id="s1", title="Le quai", environment_desc="subway", intention_scene="malaise")]
    state = plan_room_state(arc)
    from src.editor.document import EditorDocument

    scene, _ = build_next_scene(
        EditorDocument(title="V"), state, _brief(),
        director=FakeContractAgent(), drafters=_LongDrafter(), reviewer=FakeReviewer(),
    )
    assert scene.shots
    assert all(sh.duree_s <= horizon for sh in scene.shots), [sh.duree_s for sh in scene.shots]
    # 6 s → scindé en 2 sous-plans ⇒ plus de plans que le contrat (2) ne l'imposait.
    assert len(scene.shots) > 2
