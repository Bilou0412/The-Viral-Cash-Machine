"""Couche FORMATS — le catalogue (features) + le dispatcher (idée+format → EditorDocument).

Prouve le rétrofit : les DEUX structures existantes (aventure CYOA #1, scènes #2) passent
maintenant par UN seul contrat, offline via les décomposeurs Fake (aucune clé OpenAI).
"""

import pytest

pytest.importorskip("pydantic")

from src.editor.document import EditorDocument
from src.features.formats import (
    DEFAULT_FORMAT,
    UnknownFormatError,
    get_format,
    list_formats,
)
from src.studio.api.services.formats import build_format_document


def test_catalog_lists_the_hardcoded_formats():
    ids = [f.id for f in list_formats()]
    assert ids[0] == "aventure"          # #1 (déjà codé en dur)
    assert "scenes" in ids               # #2
    assert "systeme" in ids              # #3 (image → système expliqué)
    assert DEFAULT_FORMAT == "aventure"  # = défaut de Episode.format
    assert get_format("scenes").label and get_format("scenes").tagline


def test_catalog_rejects_unknown_format():
    with pytest.raises(UnknownFormatError):
        get_format("amour")   # « Amour à choix » pas encore au catalogue


def test_dispatcher_builds_a_document_for_each_format_offline():
    """Un SEUL appel construit un EditorDocument non vide pour CHAQUE format (Fake)."""
    for fmt in list_formats():
        doc = build_format_document(
            fmt.id, "une courte vidéo verticale", openai_key=None,
            options={"char_left_name": "Léa", "char_right_name": "Tom",
                     "n_scenes": 1, "n_rounds": 1, "n_steps": 1,
                     # le format 'systeme' exige une image (ignorée par les autres) :
                     "image": "https://example.com/system.png"},
        )
        assert isinstance(doc, EditorDocument)
        assert doc.bricks, f"le format '{fmt.id}' a produit un document vide"


def test_dispatcher_rejects_unknown_format():
    with pytest.raises(UnknownFormatError):
        build_format_document("amour", "idée", openai_key=None)
