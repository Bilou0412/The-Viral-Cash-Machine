"""Tests du catalogue de modèles (E4) — descripteur de formulaire + recherche filtrée.

Client Replicate factice → hors-ligne, host-runnable (model_catalog n'importe pas sqlalchemy).
"""

from typing import Any, Dict, List, Tuple

import pytest

pytest.importorskip("pydantic")

from src.studio.api.services.model_catalog import (  # noqa: E402
    clear_cache,
    form_descriptor,
    search_models,
)


class FakeClient:
    def __init__(
        self,
        schemas: Dict[str, Tuple[str, Dict[str, Any]]],
        results: List[Dict[str, Any]],
    ) -> None:
        self.schemas = schemas
        self.results = results

    def model_version_schema(self, model_ref: str) -> Tuple[str, Dict[str, Any]]:
        return self.schemas[model_ref]

    def search(self, query: str) -> List[Dict[str, Any]]:
        return list(self.results)


_VIDEO_SCHEMA = {
    "properties": {
        "prompt": {"type": "string", "x-order": 0, "description": "the prompt"},
        "image": {"type": "string", "format": "uri", "x-order": 1},
        "duration": {"type": "integer", "x-order": 2, "default": 5},
        "mood": {
            "type": "string",
            "enum": ["calm", "tense"],
            "x-order": 3,
            "default": "calm",
        },
    },
    "required": ["prompt", "image", "duration"],
}


def test_form_descriptor_maps_schema():
    clear_cache()
    client = FakeClient({"o/m": ("ver1", _VIDEO_SCHEMA)}, [])
    fd = form_descriptor("o/m", client)
    assert fd.version_id == "ver1"
    # ordonné par x-order
    assert [f.name for f in fd.fields] == ["prompt", "image", "duration", "mood"]
    by = {f.name: f for f in fd.fields}
    assert by["prompt"].required is True and by["prompt"].type == "string"
    assert by["image"].type == "file"                 # format uri → file
    assert by["duration"].type == "integer" and by["duration"].default == 5
    assert by["mood"].type == "enum" and by["mood"].enum == ["calm", "tense"]
    assert by["mood"].required is False


def test_form_descriptor_business_labels():
    # Avec `kind`, chaque input reçoit un libellé métier FR (via le contrat) ;
    # les champs hors contrat reçoivent le nom brut embelli.
    clear_cache()
    client = FakeClient({"o/m": ("ver1", _VIDEO_SCHEMA)}, [])
    by = {f.name: f for f in form_descriptor("o/m", client, kind="video").fields}
    assert by["prompt"].label == "Mouvement / action"
    assert by["image"].label == "Image de départ"
    assert by["duration"].label == "Durée (s)"
    assert by["mood"].label == "Mood"  # hors contrat → nom brut embelli
    # Sans `kind`, repli embelli pour tous.
    clear_cache()
    no_kind = {f.name: f for f in form_descriptor("o/m", client).fields}
    assert no_kind["prompt"].label == "Prompt"


def test_search_filters_by_contract():
    clear_cache()
    bad_schema = {  # pas d'`image` → ne satisfait pas le contrat vidéo
        "properties": {"prompt": {"type": "string"}, "duration": {"type": "integer"}},
        "required": ["prompt", "duration"],
    }
    client = FakeClient(
        {"o/good": ("v", _VIDEO_SCHEMA), "o/bad": ("v", bad_schema)},
        [
            {"owner": "o", "name": "good", "description": "ok"},
            {"owner": "o", "name": "bad", "description": "nope"},
        ],
    )
    cards = search_models("video", "x", client)
    assert [c.name for c in cards] == ["good"]
    assert cards[0].owner == "o"


def test_search_aliases_satisfy_required():
    clear_cache()
    # `image_input` est un alias accepté du champ requis `image` (contrat vidéo)
    alias_schema = {
        "properties": {
            "prompt": {"type": "string"},
            "image_input": {"type": "string", "format": "uri"},
            "duration": {"type": "integer"},
        },
        "required": ["prompt", "image_input", "duration"],
    }
    client = FakeClient(
        {"o/alias": ("v", alias_schema)},
        [{"owner": "o", "name": "alias"}],
    )
    assert [c.name for c in search_models("video", "q", client)] == ["alias"]


def test_search_unknown_kind_raises():
    clear_cache()
    with pytest.raises(KeyError):
        search_models("nope", "q", FakeClient({}, []))
