"""Tests de la bibliothèque de prompts — les règles d'or sont vérifiables."""

from src.features.scripting import prompts as P

VOICE = "a young hoarse whispering male voice"
LINE = "Tu vivras l'horreur avec moi."


def test_dialogue_exact_et_verbatim():
    """Règle 2-3 : réplique exacte entre guillemets, voix verbatim."""
    p = P.face_cam_dilemma("A gaunt man", VOICE, "whispering", LINE)
    assert f'"{LINE}"' in p
    assert VOICE in p  # la description de voix passe telle quelle


def test_maniere_avant_la_replique():
    """Règle 2 : la manière de dire précède la réplique."""
    p = P.face_cam_dilemma("A gaunt man", VOICE, "whispering", LINE)
    assert p.index("whispering") < p.index(LINE)


def test_camera_statique_sur_tous_les_clips():
    """Règle 6 : le bloc anti-dérive est présent sur chaque template clip."""
    clips = [
        P.face_cam_dilemma("x", VOICE, "whispering", LINE),
        P.action_sequence("x", "descends", "a mine"),
        P.environment_showcase("a mine", "hanging rocks"),
        P.fatal_outcome("x", "drops a rock", "you scream"),
        P.survival_outcome("x", "steps back"),
        P.epilogue_other_path("y", "walks a corridor"),
        P.narrator_audition(VOICE, LINE),
    ]
    for p in clips:
        assert P.STATIC_CAMERA in p


def test_jamais_de_texte_a_l_image():
    """Règle 5 : interdiction de texte, partout (clips et images)."""
    everything = [
        P.face_cam_dilemma("x", VOICE, "whispering", LINE),
        P.choice_image("a rope bridge", "a lava cave"),
        P.environment_showcase("a mine", "hanging rocks"),
    ]
    for p in everything:
        assert P.NO_TEXT in p


def test_compacite():
    """Règle 1 : court et dense — aucun template ne dépasse ~120 mots."""
    p = P.face_cam_dilemma(
        "A tall gaunt man in a tattered coat", VOICE, "whispering", LINE
    )
    assert len(p.split()) < 120


def test_audition_sans_ambiance():
    """Le sample narrateur doit être clonable : voix seule, pas d'ambiance."""
    p = P.narrator_audition(VOICE, LINE)
    assert P.VOICE_ONLY_AUDIO in p
