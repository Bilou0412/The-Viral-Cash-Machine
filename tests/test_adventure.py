"""Tests du script d'aventure (phase S).

Deux contrats :
1. Le schéma `AdventureScript` est immuable, strict, et valide ses invariants
   (3 rounds, exactement 1 choix fatal par round). Round-trip JSON + export.
2. Chaque champ remplit le BON slot des templates de `prompts.py` — c'est le
   cœur du plan : prouver que le script alimente le pipeline de prompts.
"""

import json

import pytest

pydantic = pytest.importorskip("pydantic")

from src.features.scripting import (  # noqa: E402
    AdventureScript,
    Choice,
    Round,
    VoiceProfile,
    export_schema,
)
from src.features.scripting.adventure import MAX_ROUNDS  # noqa: E402
from src.features.scripting import adventure_to_prompts as A2P  # noqa: E402
from src.features.scripting import prompts as P  # noqa: E402


# ---------------------------------------------------------------------------
# Fabriques de fixtures — un script valide construit à la main
# ---------------------------------------------------------------------------

def _round(n: int, fatal_first: bool = True) -> Round:
    """Round valide et distinctif (les valeurs encodent n pour tracer les slots)."""
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


def _script() -> AdventureScript:
    return AdventureScript(
        char_left_name="Étienne",
        char_right_name="Mathilde",
        char_left_desc="a tall gaunt man in a soaked miner's coat",
        char_right_desc="a wiry woman with a cracked lantern",
        char_left_voice=VoiceProfile(description="a young hoarse whispering male voice"),
        char_right_voice=VoiceProfile(description="a low steady breathy female voice"),
        char_left_personality_fr="Un mineur calme qui connaît la galerie.",
        char_right_personality_fr="Une femme pressée, prête à tout.",
        char_left_intro_line_fr="Moi, c'est Étienne. Suis-moi.",
        char_right_intro_line_fr="Moi, c'est Mathilde. Choisis-moi ou tu restes ici.",
        transition_narration_fr="Si tu as choisi Étienne...",
        rounds=(_round(1), _round(2, fatal_first=False), _round(3)),
        epilogue_other_desc="walking a parallel corridor, fading into darkness",
        epilogue_narration_fr="Si tu avais choisi l'autre...",
    )


# ---------------------------------------------------------------------------
# 1. Schéma : validation, invariants, round-trip, export
# ---------------------------------------------------------------------------

def test_script_valide():
    s = _script()
    assert len(s.rounds) == 3
    assert s.char_left_name == "Étienne"


def test_creator_descriptions_respectees():
    """Contrat de création : si le créateur décrit un perso, c'est respecté."""
    from src.features.scripting.fake_adventure_decomposer import FakeAdventureDecomposer

    dec = FakeAdventureDecomposer()
    s = dec.decompose_adventure(
        "grotte", "Léo", "Sam",
        char_left_desc="a tall hooded figure with a lantern",
        char_right_desc="a short nervous man in a raincoat",
    )
    assert s.char_left_desc == "a tall hooded figure with a lantern"
    assert s.char_right_desc == "a short nervous man in a raincoat"
    # vide → invention par défaut (non vide)
    s2 = dec.decompose_adventure("grotte", "Léo", "Sam")
    assert s2.char_left_desc and s2.char_right_desc


def test_intro_personnalisee_par_perso():
    """R1+P2 : chaque perso a un caractère + une réplique d'intro (conseil/réponse).

    Les répliques ne contiennent plus « choisis-moi » ni le nom (le NARRATEUR dit
    les noms, P1) ; ce sont un conseil et une réponse, distincts.
    """
    s = _script()
    assert s.char_left_personality_fr and s.char_right_personality_fr
    assert s.char_left_intro_line_fr and s.char_right_intro_line_fr
    assert s.char_left_intro_line_fr != s.char_right_intro_line_fr


def test_round_exactement_un_fatal():
    """model_validator : 0 ou 2 choix fatals doivent être rejetés."""
    base = _round(1)
    with pytest.raises(Exception):  # 0 fatal
        Round(**{
            **base.model_dump(),
            "choices": (
                base.choices[0].model_copy(update={"is_fatal": False}),
                base.choices[1].model_copy(update={"is_fatal": False}),
            ),
        })
    with pytest.raises(Exception):  # 2 fatals
        Round(**{
            **base.model_dump(),
            "choices": (
                base.choices[0].model_copy(update={"is_fatal": True}),
                base.choices[1].model_copy(update={"is_fatal": True}),
            ),
        })


def test_script_accepte_n_rounds():
    """Composition libre : N rounds (plus seulement 3) sont valides."""
    s = _script()
    two = AdventureScript(**{**s.model_dump(), "rounds": (_round(1), _round(2))})
    assert len(two.rounds) == 2
    five = AdventureScript(
        **{**s.model_dump(), "rounds": tuple(_round(i) for i in range(1, 6))}
    )
    assert len(five.rounds) == 5


def test_script_rejette_rounds_hors_bornes():
    """0 round, ou plus que MAX_ROUNDS, restent rejetés."""
    s = _script()
    with pytest.raises(Exception):  # aucun round
        AdventureScript(**{**s.model_dump(), "rounds": ()})
    with pytest.raises(Exception):  # au-delà de la borne haute
        AdventureScript(
            **{
                **s.model_dump(),
                "rounds": tuple(_round(i) for i in range(MAX_ROUNDS + 1)),
            }
        )


def test_extra_fields_interdits():
    """Critique pour le structured output : le LLM ne peut pas halluciner de champs."""
    s = _script()
    with pytest.raises(Exception):
        AdventureScript.model_validate({**s.model_dump(), "hallucinated": True})


def test_frozen():
    s = _script()
    with pytest.raises(Exception):
        s.char_left_name = "Autre"  # type: ignore[misc]


def test_json_round_trip():
    s = _script()
    restored = AdventureScript.model_validate_json(s.model_dump_json())
    assert restored == s


def test_export_schema(tmp_path):
    out = export_schema(str(tmp_path / "adventure.schema.json"))
    schema = json.loads(open(out, encoding="utf-8").read())
    assert schema["title"] == "AdventureScript"
    assert "$defs" in schema


# ---------------------------------------------------------------------------
# 2. Intégration image-first → prompts.py — frame (visuel) vs motion (mouvement)
# ---------------------------------------------------------------------------

def _rp(s):
    return A2P.round_prompts(
        s.rounds[0], s.char_left_name, s.char_left_desc, s.char_left_voice.description
    )


def test_face_cam_motion_porte_la_replique_et_la_voix_verbatim():
    """La réplique FR exacte + la voix verbatim vivent dans le MOTION du face-cam."""
    s = _script()
    rnd = s.rounds[0]
    rp = _rp(s)
    assert f'"{rnd.character_line_fr}"' in rp.character.motion
    assert s.char_left_voice.description in rp.character.motion
    # la manière précède la réplique
    assert rp.character.motion.index(rnd.character_delivery) < rp.character.motion.index(
        rnd.character_line_fr
    )


def test_separation_look_mouvement():
    """Le look (apparence, DA) est dans la FRAME ; jamais dans le MOTION."""
    s = _script()
    rp = _rp(s)
    # le visage/apparence du perso est décrit dans la frame, pas re-décrit dans le motion
    assert s.char_left_desc in rp.character.frame
    assert s.char_left_desc not in rp.character.motion
    for beat in rp.video_beats():
        assert P.DA in beat.frame          # la DA vit dans l'image
        assert P.DA not in beat.motion     # jamais re-décrite dans la vidéo
        assert "Animate from the first frame" in beat.motion


def test_action_motion_controle_la_vitesse():
    """Le motion d'action impose la vitesse calme (corrige le 'court')."""
    s = _script()
    rnd = s.rounds[0]
    rp = _rp(s)
    assert rnd.action_desc in rp.action.motion
    assert P.PACE_CALM in rp.action.motion
    # l'environnement est un atome VISUEL → dans la frame
    assert rnd.environment_desc in rp.action.frame
    assert rnd.environment_desc in rp.environment.frame
    assert rnd.danger_desc in rp.environment.frame


def test_choix_deux_images_distinctes():
    """Une image par option, dans l'ordre, avec l'environnement du round."""
    s = _script()
    rnd = s.rounds[0]
    rp = _rp(s)
    assert rnd.choices[0].image_desc in rp.choice_images[0]
    assert rnd.choices[1].image_desc in rp.choice_images[1]
    assert rp.choice_images[0] != rp.choice_images[1]
    for img in rp.choice_images:
        assert rnd.environment_desc in img


def test_issues_fatale_et_survie():
    """Mouvements de mort/survie dans les motions ; apparence dans les frames."""
    s = _script()
    rnd = s.rounds[0]
    rp = _rp(s)
    assert rnd.fatal_kill_desc in rp.fatal.motion
    assert rnd.fatal_pov_reaction in rp.fatal.motion
    assert rnd.survival_outcome_desc in rp.survival.motion
    assert s.char_left_desc in rp.fatal.frame and s.char_left_desc in rp.survival.frame


def test_voix_perso_identique_entre_clips_du_meme_perso():
    """Règle d'or 3 : le perso suivi garde EXACTEMENT la même voix sur tous ses clips."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    voice = s.char_left_voice.description
    for rp in rps:
        assert voice in rp.character.motion
    assert all(s.char_right_voice.description not in rp.character.motion for rp in rps)


def test_six_images_de_choix_sur_trois_rounds():
    """3 rounds × 2 options = 6 images de choix, non vides."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    images = [img for rp in rps for img in rp.choice_images]
    assert len(images) == 6
    assert all(img.strip() for img in images)


def test_toute_video_a_une_premiere_frame():
    """RÈGLE image-first : chaque plan vidéo a une frame ET un motion non vides."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    beats = [b for rp in rps for b in rp.video_beats()]
    beats.append(A2P.epilogue_beat(s, "left"))
    for b in beats:
        assert b.frame.strip() and b.motion.strip()
        assert "First-person POV" in b.frame


def test_epilogue_montre_l_autre_perso():
    """L'épilogue suit l'AUTRE personnage que celui du chemin suivi."""
    s = _script()
    epi_left = A2P.epilogue_beat(s, "left")   # suivi=gauche → épilogue montre droite
    assert s.char_right_desc in epi_left.frame
    assert s.char_left_desc not in epi_left.frame
    assert s.epilogue_other_desc in epi_left.motion
    epi_right = A2P.epilogue_beat(s, "right")
    assert s.char_left_desc in epi_right.frame


def test_regles_d_or_sur_toutes_les_images():
    """No-text + DA + POV + mains sur CHAQUE image (frames + images de choix)."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    images = []
    for rp in rps:
        images += rp.all_image_prompts()
    images.append(A2P.epilogue_beat(s, "left").frame)
    for p in images:
        assert P.NO_TEXT in p
        assert P.DA in p
        assert "First-person POV" in p
        assert P.POV_HANDS in p


def test_tous_les_champs_round_sont_consommes():
    """Garde-fou : chaque champ texte EN/FR d'un round apparaît dans un prompt."""
    s = _script()
    rnd = s.rounds[0]
    rp = _rp(s)
    blob = " ||| ".join(
        [b.frame + " " + b.motion for b in rp.video_beats()] + list(rp.choice_images)
    )
    for field in (
        rnd.action_desc,
        rnd.environment_desc,
        rnd.danger_desc,
        rnd.character_delivery,
        rnd.character_line_fr,
        rnd.choices[0].image_desc,
        rnd.choices[1].image_desc,
        rnd.fatal_kill_desc,
        rnd.fatal_pov_reaction,
        rnd.survival_outcome_desc,
    ):
        assert field in blob, f"champ non consommé par le mapping : {field!r}"
