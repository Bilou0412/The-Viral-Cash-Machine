"""Tests de la bibliothèque de prompts — règles d'or + doctrine POV/FPS."""

from src.features.scripting import prompts as P

NAME = "Étienne"
DESC = "a gaunt pale man in a soaked miner's jacket"
VOICE = "a young hoarse whispering male voice"
LINE = "Tu me suis, ou tu pars. Choisis vite."


def test_dialogue_exact_et_verbatim():
    """Règle 2-3 : réplique exacte entre guillemets, voix verbatim."""
    p = P.character_choice(NAME, DESC, VOICE, "whispering", LINE)
    assert f'"{LINE}"' in p
    assert VOICE in p


def test_maniere_avant_la_replique():
    """Règle 2 : la manière de dire précède la réplique."""
    p = P.character_choice(NAME, DESC, VOICE, "whispering", LINE)
    assert p.index("whispering") < p.index(LINE)


def test_pov_et_mains_sur_tous_les_clips():
    """Doctrine POV/FPS : first-person + mains visibles sur chaque template."""
    clips = [
        P.character_choice(NAME, DESC, VOICE, "whispering", LINE),
        P.action_sequence(NAME, DESC, "descends", "a mine"),
        P.environment_showcase(NAME, "a mine", "hanging rocks"),
        P.fatal_outcome(NAME, DESC, "drops a rock", "we scream"),
        P.survival_outcome(NAME, DESC, "steps back"),
        P.epilogue_other_path("Marc", "a wiry man", "walks a corridor"),
        P.choice_image(NAME, "a rope bridge", "a lava cave"),
    ]
    for p in clips:
        assert "First-person POV" in p
        assert P.POV_HANDS in p


def test_da_partout():
    """DA unique : la constante DA est présente sur chaque asset (cohérence)."""
    assets = [
        P.action_sequence(NAME, DESC, "descends", "a mine"),
        P.character_choice(NAME, DESC, VOICE, "whispering", LINE),
        P.choice_image(NAME, "a bridge", "a cave"),
        P.fatal_outcome(NAME, DESC, "drops a rock", "we scream"),
    ]
    for p in assets:
        assert P.DA in p


def test_protagoniste_present_partout():
    """Le perso est toujours dans le cadre — son nom apparaît sur chaque plan."""
    assets = [
        P.action_sequence(NAME, DESC, "descends", "a mine"),
        P.environment_showcase(NAME, "a mine", "rocks"),
        P.character_choice(NAME, DESC, VOICE, "whispering", LINE),
        P.choice_image(NAME, "a bridge", "a cave"),
        P.survival_outcome(NAME, DESC, "steps back"),
    ]
    for p in assets:
        assert NAME in p


def test_jamais_de_texte_a_l_image():
    """Règle 5 : interdiction de texte, partout (clips et images)."""
    everything = [
        P.character_choice(NAME, DESC, VOICE, "whispering", LINE),
        P.choice_image(NAME, "a rope bridge", "a lava cave"),
        P.environment_showcase(NAME, "a mine", "hanging rocks"),
    ]
    for p in everything:
        assert P.NO_TEXT in p


def test_compacite():
    """Règle 1 : court et dense — le face-cam reste sous ~130 mots."""
    p = P.character_choice(NAME, DESC, VOICE, "whispering", LINE)
    assert len(p.split()) < 130


def test_audition_sans_ambiance():
    """Le sample narrateur doit être clonable : voix seule, pas d'ambiance."""
    p = P.narrator_audition(VOICE, LINE)
    assert P.VOICE_ONLY_AUDIO in p
