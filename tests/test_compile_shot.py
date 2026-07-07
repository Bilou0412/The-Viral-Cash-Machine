"""T-DESC — compilateur 3 niveaux : héritage scène→plan + recompile + migration v4→v5."""

import pytest

pytest.importorskip("pydantic")

from src.editor.capabilities import validate_clip
from src.editor.compile_shot import (
    compile_image_prompt,
    compile_motion_prompt,
    recompile_document,
    resolve_shot,
)
from src.editor.document import (
    Cadre,
    Camera,
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    GenNode,
    LocationEntry,
    Lumiere,
    PersonnagePresent,
    Scene,
    ShotBrief,
    TimelinePlacement,
)
from src.editor.migrations import upgrade_document
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer


def _doc(scene: Scene, brief: ShotBrief) -> tuple[EditorDocument, Scene]:
    """Un doc minimal : 1 décor bible, 1 perso bible, 1 scène, 1 brique-plan."""
    clip = ClipBrick(
        id="sh1", kind="video",
        image=GenNode(model_ref="m", params={"prompt": ""}),
        motion=GenNode(model_ref="v", params={"prompt": "", "image": "x"}),
        shot=brief, placement=TimelinePlacement(track=0, start=0.0, duration=4.0),
    )
    scene = scene.model_copy(update={"shot_ids": ["sh1"]})
    doc = EditorDocument(
        bricks=[clip], scenes=[scene],
        bible=[CharacterEntry(id="lea", name="Léa", appearance="red-haired teen", wardrobe="blue coat")],
        location_bible=[LocationEntry(ref="loc1", lieu="abandoned subway",
                                      lumiere_base=Lumiere(sources="dim base light"))],
    )
    return doc, scene


# -- compilateur + héritage ---------------------------------------------------

def test_image_prompt_resolves_location_and_character():
    scene = Scene(id="s1", location_ref="loc1", moment_jour="night",
                  lumiere_ambiante=Lumiere(sources="cold flicker"))
    brief = ShotBrief(cadre=Cadre(taille_plan="close-up"),
                      personnages_presents=[PersonnagePresent(ref="lea", expression="terrified")])
    doc, scene = _doc(scene, brief)
    r = resolve_shot(doc, scene, brief)
    out = compile_image_prompt(r)
    assert "close-up" in out and "Léa (red-haired teen)" in out
    assert "abandoned subway" in out and "night" in out
    assert "cold flicker" in out           # lumière héritée de la scène


def test_lumiere_inheritance_and_override():
    scene = Scene(id="s1", location_ref="loc1", lumiere_ambiante=Lumiere(sources="scene ambient"))
    # Sans override → hérite de la scène.
    d, sc = _doc(scene, ShotBrief())
    assert resolve_shot(d, sc, ShotBrief()).lumiere.sources == "scene ambient"
    # Avec override plan → gagne.
    over = ShotBrief(lumiere_override=Lumiere(sources="lightning flash"))
    d2, sc2 = _doc(scene, over)
    assert resolve_shot(d2, sc2, over).lumiere.sources == "lightning flash"


def test_motion_prompt_uses_movement_and_delta():
    scene = Scene(id="s1", location_ref="loc1")
    brief = ShotBrief(
        camera=Camera(type="slow push in"),
        personnages_presents=[PersonnagePresent(ref="lea", action="turns", etat_debut="still", etat_fin="running")],
    )
    d, sc = _doc(scene, brief)
    out = compile_motion_prompt(resolve_shot(d, sc, brief))
    assert "camera slow push in" in out and "turns" in out and "still to running" in out


# -- recompile + rétro-compat -------------------------------------------------

def test_recompile_updates_image_and_motion():
    scene = Scene(id="s1", location_ref="loc1")
    brief = ShotBrief(cadre=Cadre(taille_plan="wide shot"), camera=Camera(type="static"))
    doc, _ = _doc(scene, brief)
    recompile_document(doc)
    clip = doc.bricks[0]
    assert isinstance(clip, ClipBrick)
    assert "wide shot" in clip.image.params["prompt"]
    assert clip.motion is not None and "camera static" in clip.motion.params["prompt"]


def test_backward_compat_shot_none_unchanged():
    """INVARIANT : une brique sans `shot` n'est jamais touchée."""
    clip = ClipBrick(id="a", kind="photo", image=GenNode(model_ref="m", params={"prompt": "wide, cinematic"}),
                     shot=None, placement=TimelinePlacement(track=0, start=0.0, duration=3.0))
    doc = EditorDocument(bricks=[clip])
    before = doc.model_dump_json()
    recompile_document(doc)
    assert doc.model_dump_json() == before


def test_v4_doc_migrates_to_v5():
    """Un doc v4 (shot plat) → décor synthétisé en LocationEntry, valide en v5."""
    raw = {
        "schema_version": 4, "title": "old",
        "scenes": [{"id": "s1", "environment_photo_ref": "env", "shot_ids": ["p1"]}],
        "bricks": [
            {"type": "clip", "id": "env", "kind": "photo",
             "image": {"model_ref": "m", "params": {"prompt": "x"}},
             "shot": {"decor": "dark alley", "lumiere": "one lamp"}},
            {"type": "clip", "id": "p1", "kind": "video",
             "image": {"model_ref": "m", "params": {"prompt": "v4 cached prompt"}},
             "motion": {"model_ref": "v", "params": {"prompt": "static camera", "image": "x", "duration": 4.0}},
             "shot": {"decor": "dark alley", "lumiere": "one lamp", "cadrage": "close-up",
                      "characters": [{"ref": "", "name": "Bob", "action": "runs"}]}},
        ],
    }
    doc = upgrade_document(raw)
    assert doc.schema_version == 5
    assert doc.location_bible and doc.location_bible[0].lieu == "dark alley"
    assert doc.scenes[0].location_ref == doc.location_bible[0].ref
    p1 = next(b for b in doc.bricks if b.id == "p1")
    assert isinstance(p1, ClipBrick) and p1.shot is not None
    assert p1.shot.cadre.taille_plan == "close-up"
    assert p1.shot.personnages_presents[0].action == "runs"
    for b in doc.bricks:
        if isinstance(b, ClipBrick):
            assert validate_clip(b) == {}


# -- décomposeur Fake → descripteur 3 niveaux --------------------------------

def test_fake_decomposer_builds_three_levels():
    plan = FakeSceneDecomposer().decompose_video("un métro hanté", n_scenes=2)
    doc = scene_plan_to_document(plan, title="T")
    assert doc.location_bible and doc.bible and doc.bible[0].name == "Léa"
    assert doc.meta.ratio == "9:16"
    clips = [b for b in doc.bricks if isinstance(b, ClipBrick)]
    people_shot = next(c for c in clips if c.shot and c.shot.personnages_presents)
    assert "Léa" in people_shot.image.params["prompt"]       # perso résolu dans le prompt
    assert "subway" in people_shot.image.params["prompt"]     # décor hérité de la scène
    for c in clips:
        assert validate_clip(c) == {}
