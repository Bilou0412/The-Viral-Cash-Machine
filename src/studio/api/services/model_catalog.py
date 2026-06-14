"""Catalogue de modèles — schémas d'arguments + recherche filtrée (E4).

Alimente l'inspecteur dynamique de l'éditeur : pour un `model_ref`, renvoie un
descripteur de formulaire (champs, types, défauts, enum, requis) dérivé du schéma
d'inputs OpenAPI du modèle Replicate ; et une recherche qui ne retourne que les
modèles satisfaisant le **contrat de capacité** d'une brique (cf. registry).

Le client Replicate est INJECTABLE (`CatalogClient`) → tests hors-ligne. En prod,
`ReplicateCatalogClient` appelle l'API HTTP Replicate (PAS le MCP, réservé aux agents).
Cache en mémoire par `model_ref` (schémas immuables par version).
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel

from ....features.compositing.registry import get_contract, model_satisfies

# ---------------------------------------------------------------------------
# Descripteurs (réponse API)
# ---------------------------------------------------------------------------


class FormField(BaseModel):
    name: str
    type: str            # string | integer | number | boolean | enum | file | array
    required: bool
    default: Any = None
    enum: Optional[List[str]] = None
    description: str = ""
    order: int = 999


class FormDescriptor(BaseModel):
    model_ref: str
    version_id: str
    fields: List[FormField]


class ModelCard(BaseModel):
    owner: str
    name: str
    cover: Optional[str] = None
    description: str = ""


# ---------------------------------------------------------------------------
# Client (injectable)
# ---------------------------------------------------------------------------


class CatalogClient(Protocol):
    def model_version_schema(self, model_ref: str) -> Tuple[str, Dict[str, Any]]:
        """(version_id, input_schema OpenAPI) du modèle (`owner/name`)."""
        ...

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Modèles bruts {owner, name, cover_image_url, description, ...}."""
        ...


_API = "https://api.replicate.com/v1"


class ReplicateCatalogClient:
    """Client HTTP Replicate (prod). Token via REPLICATE_API_TOKEN."""

    def _get(self, path: str) -> Dict[str, Any]:
        token = os.environ.get("REPLICATE_API_TOKEN", "")
        req = urllib.request.Request(
            f"{_API}{path}", headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data: Dict[str, Any] = json.load(r)
            return data

    def model_version_schema(self, model_ref: str) -> Tuple[str, Dict[str, Any]]:
        owner, name = model_ref.split("/", 1)
        data = self._get(f"/models/{owner}/{name}")
        version = data.get("latest_version") or {}
        version_id = str(version.get("id", ""))
        schema = (
            version.get("openapi_schema", {})
            .get("components", {})
            .get("schemas", {})
            .get("Input", {})
        )
        return version_id, schema

    def search(self, query: str) -> List[Dict[str, Any]]:
        # Replicate model search (best-effort ; le résultat est filtré ensuite).
        data = self._get(f"/models?query={urllib.parse.quote(query)}")
        results = data.get("results", [])
        return list(results) if isinstance(results, list) else []


# ---------------------------------------------------------------------------
# Cache mémoire (schémas immuables par version)
# ---------------------------------------------------------------------------

_schema_cache: Dict[str, Tuple[str, Dict[str, Any]]] = {}


def _cached_schema(
    client: CatalogClient, model_ref: str
) -> Tuple[str, Dict[str, Any]]:
    hit = _schema_cache.get(model_ref)
    if hit is None:
        hit = client.model_version_schema(model_ref)
        _schema_cache[model_ref] = hit
    return hit


def clear_cache() -> None:
    _schema_cache.clear()


# ---------------------------------------------------------------------------
# Conversion schéma OpenAPI → descripteur de formulaire
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "string": "string",
}


def _field_type(prop: Dict[str, Any]) -> str:
    if prop.get("enum"):
        return "enum"
    if prop.get("format") == "uri":
        return "file"
    return _TYPE_MAP.get(str(prop.get("type", "string")), "string")


def _input_properties(schema: Dict[str, Any]) -> List[str]:
    return list(schema.get("properties", {}).keys())


def form_descriptor(model_ref: str, client: CatalogClient) -> FormDescriptor:
    """Descripteur de formulaire pour l'inspecteur (champs triés par x-order)."""
    version_id, schema = _cached_schema(client, model_ref)
    props: Dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = [
        FormField(
            name=name,
            type=_field_type(prop),
            required=name in required,
            default=prop.get("default"),
            enum=prop.get("enum"),
            description=str(prop.get("description", "")),
            order=int(prop.get("x-order", 999)),
        )
        for name, prop in props.items()
    ]
    fields.sort(key=lambda f: (f.order, f.name))
    return FormDescriptor(model_ref=model_ref, version_id=version_id, fields=fields)


def search_models(kind: str, query: str, client: CatalogClient) -> List[ModelCard]:
    """Modèles correspondant à `query` ET satisfaisant le contrat de la brique."""
    contract = get_contract(kind)  # KeyError si kind inconnu
    cards: List[ModelCard] = []
    for raw in client.search(query):
        owner = str(raw.get("owner", ""))
        name = str(raw.get("name", ""))
        if not owner or not name:
            continue
        try:
            _, schema = _cached_schema(client, f"{owner}/{name}")
        except Exception:
            continue  # modèle illisible → on l'ignore
        if not model_satisfies(contract, _input_properties(schema)):
            continue
        cards.append(
            ModelCard(
                owner=owner,
                name=name,
                cover=raw.get("cover_image_url"),
                description=str(raw.get("description", "")),
            )
        )
    return cards
