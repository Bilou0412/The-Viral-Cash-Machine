"""`AdventureScript` → `VideoPlan` (le rail v5) — le CYOA horreur devient un doc v5.

Règle « rail unique » (`.claude/rules/architecture.md`) : un format ne construit PAS ses
prompts à la main. On mappe donc la STRUCTURE CYOA (2 persos, N manches, choix/fatal, épilogue)
sur le modèle de scènes v5 (`VideoPlan → ScenePlan → ShotPlan`), puis `scene_plan_to_document`
+ `compile_shot` font le reste (prompts courts EN, prénoms FR, discipline durée, descripteur).

Mapping : 1 manche = 1 SCÈNE ; chaque beat (action / danger / face-cam / choix ×2 / fatal /
survie) = 1 PLAN. Les persos-en-action → `personnages` (structuré) ; les plans « illustration »
(danger, choix, fatal, survie, épilogue) → `sujet` (sujet libre EN). Le POV/DA horreur passe par
`meta.style_rendu` (hérité par tous les plans). Convention : visuels EN, parlé FR.
"""

from __future__ import annotations

from ...editor.document import (
    Cadre,
    Camera,
    IntentionGlobale,
    LocationEntry,
    Lumiere,
    RenderMeta,
    Son,
)
from ..scenes.model import (
    CharacterPlan,
    ScenePlan,
    ShotCharacterPlan,
    ShotPlan,
    VideoPlan,
)
from .adventure import AdventureScript
from .themes import Theme, get_theme

_FACE = Cadre(taille_plan="extreme close-up", angle_hauteur="eye-level", focale="35mm")
_WIDE = Cadre(taille_plan="wide shot", angle_hauteur="eye-level", focale="24mm")
_MED = Cadre(taille_plan="medium shot", angle_hauteur="eye-level", focale="35mm")


def _loc(ref: str, lieu: str) -> LocationEntry:
    return LocationEntry(
        ref=ref, lieu=lieu, int_ext="interior", echelle="oppressive",
        palette="desaturated, cold shadows, sickly highlights", matieres="wet stone, rust, grime",
        lumiere_base=Lumiere(sources="a single failing light", direction="low, raking",
                             qualite="hard", temperature="cold", contraste="high-contrast"),
    )


def adventure_to_video_plan(
    script: AdventureScript, side: str = "left", theme: Theme | None = None,
) -> VideoPlan:
    """Le script d'aventure → un `VideoPlan` v5 (scènes = manches, plans = beats)."""
    th = theme or get_theme()
    foll_name = script.char_right_name if side == "right" else script.char_left_name

    cast = [
        CharacterPlan(name=script.char_left_name, appearance=script.char_left_desc,
                      traits=script.char_left_personality_fr),
        CharacterPlan(name=script.char_right_name, appearance=script.char_right_desc,
                      traits=script.char_right_personality_fr),
    ]
    # POV + DA horreur → hérités par TOUS les plans via le style. POV EN TÊTE : le
    # compilateur cape le style (~10 mots) ; le POV/FPS est la contrainte QUI DÉFINIT
    # le format (l'immersion), donc il doit survivre à la troncature — le look horreur
    # froid/désaturé, lui, remonte déjà via l'ambiance (lumière + palette du décor).
    style = ", ".join(p for p in (th.pov, th.da) if p.strip())
    meta = RenderMeta(ratio="9:16", style_rendu=style)
    intention = IntentionGlobale(
        genre="horreur interactive (à choix multiple)", ton="tendu, immersif, POV",
        arc_narratif="le spectateur suit un compagnon de manche en manche ; chaque choix peut être fatal",
    )

    scenes: list[ScenePlan] = []
    locations: list[LocationEntry] = []

    # -- INTRO : les 2 compagnons face caméra, chacun se présente (« choisis-moi ») --
    locations.append(_loc("intro_loc", "a dark liminal threshold, the two companions facing the viewer"))
    scenes.append(ScenePlan(
        id="intro", title="Intro", location_ref="intro_loc", mood="ominous, inviting dread",
        environment_desc="POV: two companions stand in the dark, facing you, waiting to be chosen",
        intention_scene="présenter les deux compagnons ; l'un ment", shots=[
            ShotPlan(id="intro_left", kind="video", duree_s=4.0,
                     narration_fr=script.char_left_intro_line_fr,
                     personnages=[ShotCharacterPlan(name=script.char_left_name,
                                                    expression="staring at you, unsettling",
                                                    action="leans toward the camera")],
                     cadre=_FACE, camera=Camera(type="slow push in"),
                     intention_plan="the left companion tries to convince you to pick them"),
            ShotPlan(id="intro_right", kind="video", duree_s=4.0,
                     narration_fr=script.char_right_intro_line_fr,
                     personnages=[ShotCharacterPlan(name=script.char_right_name,
                                                    expression="cold, pleading eyes",
                                                    action="reaches a hand toward you")],
                     cadre=_FACE, camera=Camera(type="slow push in"),
                     intention_plan="the right companion pleads to be chosen"),
            ShotPlan(id="intro_transition", kind="video", duree_s=3.0,
                     narration_fr=script.transition_narration_fr,
                     sujet="POV first-person, stepping forward into a black corridor with the chosen companion",
                     cadre=_WIDE, camera=Camera(type="slow push in"),
                     intention_plan="the viewer commits and steps into the adventure"),
        ]))

    # -- MANCHES : une SCÈNE par round, un PLAN par beat --
    for i, rnd in enumerate(script.rounds, start=1):
        ref = f"round{i}_loc"
        locations.append(_loc(ref, rnd.environment_desc))
        scenes.append(ScenePlan(
            id=f"round{i}", title=f"Manche {i}", location_ref=ref,
            environment_desc=rnd.environment_desc, mood="tense, mortal danger",
            intention_scene="avancer, affronter le danger, puis un choix qui peut tuer", shots=[
                ShotPlan(id=f"r{i}_action", kind="video", duree_s=4.0,
                         narration_fr=rnd.action_narration_fr,
                         personnages=[ShotCharacterPlan(name=foll_name, action=rnd.action_desc,
                                                        etat_debut="moving forward", etat_fin="alert")],
                         cadre=_WIDE, camera=Camera(type="slow push in"),
                         intention_plan="advance behind the companion through the hostile place"),
                ShotPlan(id=f"r{i}_danger", kind="video", duree_s=4.0,
                         narration_fr=rnd.environment_narration_fr, sujet=rnd.danger_desc,
                         cadre=_WIDE, intention_plan="reveal the physical danger of this place"),
                ShotPlan(id=f"r{i}_facecam", kind="video", duree_s=3.0,
                         narration_fr=rnd.character_line_fr,
                         personnages=[ShotCharacterPlan(name=foll_name,
                                                        expression=rnd.character_delivery or "whispering, tense")],
                         cadre=_FACE, son=Son(dialogue_voix=rnd.character_line_fr),
                         intention_plan="the companion turns and speaks the dilemma to you"),
                ShotPlan(id=f"r{i}_choiceA", kind="photo", duree_s=3.0,
                         narration_fr=rnd.choice_narration_fr, sujet=rnd.choices[0].image_desc,
                         intention_plan=f"option A — {rnd.choices[0].label_fr}"),
                ShotPlan(id=f"r{i}_choiceB", kind="photo", duree_s=3.0,
                         sujet=rnd.choices[1].image_desc,
                         intention_plan=f"option B — {rnd.choices[1].label_fr}"),
                ShotPlan(id=f"r{i}_fatal", kind="video", duree_s=4.0,
                         narration_fr=rnd.fatal_narration_fr,
                         sujet=f"{rnd.fatal_kill_desc}; POV reaction: {rnd.fatal_pov_reaction}",
                         cadre=_MED, intention_plan="the fatal outcome: the companion turns on you"),
                ShotPlan(id=f"r{i}_survival", kind="video", duree_s=4.0,
                         narration_fr=rnd.survival_narration_fr, sujet=rnd.survival_outcome_desc,
                         cadre=_MED, intention_plan="the survival outcome: you live, the story continues"),
            ]))

    # -- ÉPILOGUE : un aperçu de l'autre chemin --
    locations.append(_loc("epilogue_loc", script.epilogue_other_desc or "the path not taken"))
    scenes.append(ScenePlan(
        id="epilogue", title="Épilogue", location_ref="epilogue_loc", mood="haunting, final",
        environment_desc=script.epilogue_other_desc, intention_scene="clore sur l'autre destin", shots=[
            ShotPlan(id="epilogue_shot", kind="video", duree_s=4.0,
                     narration_fr=script.epilogue_narration_fr, sujet=script.epilogue_other_desc,
                     cadre=_WIDE, intention_plan="glimpse the fate of the companion you did not choose"),
        ]))

    return VideoPlan(
        title=f"{foll_name} — aventure horreur", meta=meta, intention_globale=intention,
        musique_score="dark ambient horror drone, sudden stingers on the choices",
        location_bible=locations, cast=cast, scenes=scenes,
    )
