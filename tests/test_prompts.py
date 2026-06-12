"""Tests de la bibliothèque de prompts — méthodologie image-first + POV/FPS."""

from src.features.scripting import prompts as P

NAME = "Étienne"
DESC = "a gaunt pale man in a soaked miner's jacket"
ENV = "a flooded mine tunnel"
VOICE = "a young hoarse whispering male voice"
LINE = "Tu me suis, ou tu pars. Choisis vite."

FRAMES = [
    P.frame_action(NAME, DESC, ENV),
    P.frame_environment(NAME, ENV, "hanging rocks"),
    P.frame_character(NAME, DESC, ENV),
    P.frame_fatal(NAME, DESC, ENV),
    P.frame_survival(NAME, DESC, ENV),
    P.choice_image(NAME, "a rope bridge", ENV),
]


def test_frames_portent_tout_le_visuel():
    """Chaque première frame : POV + mains + DA + nom du perso + no-text."""
    for f in FRAMES:
        assert "First-person POV" in f
        assert P.POV_HANDS in f
        assert P.DA in f
        assert NAME in f
        assert P.NO_TEXT in f


def test_motion_ne_redecrit_pas_le_look():
    """Les prompts de mouvement ne contiennent NI la DA NI les mains (look = image)."""
    motions = [
        P.motion_action(NAME, "descends the shaft"),
        P.motion_environment(NAME),
        P.motion_character(NAME, VOICE, "whispering", LINE),
        P.motion_fatal(NAME, "drops a rock", "we scream"),
        P.motion_survival(NAME, "climbs out"),
    ]
    for m in motions:
        assert P.DA not in m
        assert P.POV_HANDS not in m
        assert "Animate from the first frame" in m


def test_motion_action_controle_la_vitesse():
    """Le mouvement d'action impose une vitesse calme (corrige le 'court')."""
    m = P.motion_action(NAME, "descends the shaft")
    assert P.PACE_CALM in m
    assert "no running" in m


def test_motion_character_dialogue_exact_et_voix_verbatim():
    """Réplique exacte + voix verbatim + manière avant la réplique."""
    m = P.motion_character(NAME, VOICE, "whispering", LINE)
    assert f'"{LINE}"' in m
    assert VOICE in m
    assert m.index("whispering") < m.index(LINE)


def test_motion_character_voix_seule():
    """Le face-cam est en voix seule (pas d'ambiance qui pollue le clonage/mix)."""
    assert P.VOICE_ONLY_AUDIO in P.motion_character(NAME, VOICE, "whispering", LINE)


def test_frames_sans_dialogue():
    """Les images de première frame ne portent jamais le dialogue (texte interdit)."""
    f = P.frame_character(NAME, DESC, ENV)
    assert LINE not in f
