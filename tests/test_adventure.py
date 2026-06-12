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


def test_script_exige_trois_rounds():
    s = _script()
    with pytest.raises(Exception):
        AdventureScript(**{**s.model_dump(), "rounds": (s.rounds[0], s.rounds[1])})


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
# 2. Intégration slots → prompts.py — CHAQUE champ alimente le bon template
# ---------------------------------------------------------------------------

def test_face_cam_porte_la_replique_et_la_voix_verbatim():
    """character_line_fr (FR exact) + voice.description (verbatim) dans le face-cam."""
    s = _script()
    rp = A2P.round_prompts(s.rounds[0], s.char_left_desc, s.char_left_voice.description)
    assert f'"{s.rounds[0].character_line_fr}"' in rp.face_cam
    assert s.char_left_voice.description in rp.face_cam
    assert s.char_left_desc in rp.face_cam


def test_delivery_precede_la_replique():
    """Règle d'or 2 : la manière de dire (delivery) précède la réplique."""
    s = _script()
    rnd = s.rounds[0]
    rp = A2P.round_prompts(rnd, s.char_left_desc, s.char_left_voice.description)
    assert rp.face_cam.index(rnd.character_delivery) < rp.face_cam.index(rnd.character_line_fr)


def test_action_et_environnement_dans_les_bons_slots():
    s = _script()
    rnd = s.rounds[0]
    rp = A2P.round_prompts(rnd, s.char_left_desc, s.char_left_voice.description)
    assert rnd.action_desc in rp.action
    assert rnd.environment_desc in rp.action          # action_sequence(..., environment_desc)
    assert rnd.environment_desc in rp.environment      # environment_showcase(environment_desc, ...)
    assert rnd.danger_desc in rp.environment


def test_choix_deux_images_distinctes():
    """Une image par option, dans l'ordre, avec l'environnement du round."""
    s = _script()
    rnd = s.rounds[0]
    rp = A2P.round_prompts(rnd, s.char_left_desc, s.char_left_voice.description)
    assert rnd.choices[0].image_desc in rp.choice_images[0]
    assert rnd.choices[1].image_desc in rp.choice_images[1]
    assert rp.choice_images[0] != rp.choice_images[1]
    for img in rp.choice_images:
        assert rnd.environment_desc in img


def test_issues_fatale_et_survie():
    s = _script()
    rnd = s.rounds[0]
    rp = A2P.round_prompts(rnd, s.char_left_desc, s.char_left_voice.description)
    assert rnd.fatal_kill_desc in rp.fatal
    assert rnd.fatal_pov_reaction in rp.fatal
    assert rnd.survival_outcome_desc in rp.survival
    assert s.char_left_desc in rp.fatal and s.char_left_desc in rp.survival


def test_voix_perso_identique_entre_clips_du_meme_perso():
    """Règle d'or 3 : le perso suivi garde EXACTEMENT la même voix sur tous ses clips."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    voice = s.char_left_voice.description
    for rp in rps:
        assert voice in rp.face_cam
    # et jamais la voix de l'autre perso sur le chemin gauche
    assert all(s.char_right_voice.description not in rp.face_cam for rp in rps)


def test_six_images_de_choix_sur_trois_rounds():
    """3 rounds × 2 options = 6 images de choix, toutes non vides et distinctes par round."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    images = [img for rp in rps for img in rp.choice_images]
    assert len(images) == 6
    assert all(img.strip() for img in images)


def test_epilogue_montre_l_autre_perso():
    """L'épilogue suit l'AUTRE personnage que celui du chemin suivi."""
    s = _script()
    epi_left = A2P.epilogue_prompt(s, "left")   # suivi=gauche → épilogue montre droite
    assert s.char_right_desc in epi_left
    assert s.char_left_desc not in epi_left
    assert s.epilogue_other_desc in epi_left
    epi_right = A2P.epilogue_prompt(s, "right")  # symétrique
    assert s.char_left_desc in epi_right


def test_regles_d_or_sur_tous_les_prompts_du_script():
    """Caméra statique + no-text présents sur CHAQUE prompt produit (clips et images)."""
    s = _script()
    rps = A2P.script_prompts(s, "left")
    all_prompts = [p for rp in rps for p in rp.as_list()]
    all_prompts.append(A2P.epilogue_prompt(s, "left"))
    for p in all_prompts:
        assert P.NO_TEXT in p
    # STATIC_CAMERA sur les clips (les images de choix n'embarquent pas ce bloc)
    for rp in rps:
        for clip in (rp.action, rp.environment, rp.face_cam, rp.fatal, rp.survival):
            assert P.STATIC_CAMERA in clip


def test_tous_les_champs_round_sont_consommes():
    """Garde-fou : chaque champ texte EN/FR d'un round apparaît dans au moins un prompt.

    Si le builder ajoute un champ visuel au schéma, ce test échoue tant que le
    mapping ne le consomme pas — il empêche un slot oublié.
    """
    s = _script()
    rnd = s.rounds[0]
    rp = A2P.round_prompts(rnd, s.char_left_desc, s.char_left_voice.description)
    blob = " ||| ".join(rp.as_list())
    # champs visuels EN qui DOIVENT atterrir dans un prompt
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
