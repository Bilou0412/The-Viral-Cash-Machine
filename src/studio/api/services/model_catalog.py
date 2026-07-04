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

from typing import Any, Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel

from ....features.compositing.registry import (
    get_contract,
    label_for,
    model_satisfies,
)

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
    # Libellé métier FR (depuis le contrat du kind) ; repli = nom brut embelli.
    label: str = ""
    help: str = ""


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


class ReplicateCatalogClient:
    """Client catalogue via le **SDK** `replicate` (auth + User-Agent corrects).

    On NE fait PAS d'appel urllib brut : l'API Replicate est derrière Cloudflare qui
    renvoie 403 sur le User-Agent par défaut `Python-urllib`. Le SDK (déjà utilisé par
    la génération) gère auth, UA, pagination et recherche. Token = clé de l'utilisateur
    courant (B.2), passée au client SDK (plus de lecture d'env partagée).
    """

    def __init__(self, api_token: Optional[str] = None) -> None:
        self.api_token = api_token

    def _client(self) -> Any:
        from replicate.client import Client

        return Client(api_token=self.api_token) if self.api_token else Client()

    def model_version_schema(self, model_ref: str) -> Tuple[str, Dict[str, Any]]:
        model = self._client().models.get(model_ref)
        version = getattr(model, "latest_version", None)
        if version is None:  # certains modèles : prendre la 1re version listée
            versions = list(model.versions.list())
            version = versions[0] if versions else None
        version_id = str(getattr(version, "id", "")) if version else ""
        schema: Dict[str, Any] = {}
        if version is not None:
            openapi = getattr(version, "openapi_schema", None) or {}
            schema = (
                openapi.get("components", {}).get("schemas", {}).get("Input", {})
            )
        return version_id, schema

    def search(self, query: str) -> List[Dict[str, Any]]:
        try:
            page = self._client().models.search(query)
        except Exception:
            return []  # SDK sans search / erreur réseau → pas de résultat
        out: List[Dict[str, Any]] = []
        for m in page:
            out.append(
                {
                    "owner": getattr(m, "owner", ""),
                    "name": getattr(m, "name", ""),
                    "cover_image_url": getattr(m, "cover_image_url", None),
                    "description": getattr(m, "description", "") or "",
                }
            )
        return out


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


def _prettify(raw_name: str) -> str:
    """Repli quand le champ n'est pas dans le contrat : snake_case → « Titre »."""
    return raw_name.replace("_", " ").strip().capitalize()


def form_descriptor(
    model_ref: str, client: CatalogClient, kind: Optional[str] = None
) -> FormDescriptor:
    """Descripteur de formulaire pour l'inspecteur (champs triés par x-order).

    ``kind`` (image/video/voice) permet d'attacher un **libellé métier FR** à
    chaque input via le contrat du kind ; repli = nom brut embelli.
    """
    version_id, schema = _cached_schema(client, model_ref)
    props: Dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = []
    for name, prop in props.items():
        label, help_txt = (label_for(kind, name) if kind else ("", ""))
        fields.append(
            FormField(
                name=name,
                type=_field_type(prop),
                required=name in required,
                default=prop.get("default"),
                enum=prop.get("enum"),
                description=str(prop.get("description", "")),
                order=int(prop.get("x-order", 999)),
                label=label or _prettify(name),
                help=help_txt,
            )
        )
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
