"""Extraction canonique des params de brique via les contrats de capacité.

SOURCE UNIQUE DE VÉRITÉ partagée par `capabilities.validate_clip` (ce qui est
« présent ») et `compile_spec.document_to_spec` (ce qui est « lu »), pour qu'ils
ne DIVERGENT jamais : un champ jugé présent par le validateur est lu par le
compilateur sous le même nom canonique OU l'un de ses alias de contrat. Sans ce
partage, un nœud renseigné via un alias (`input_text` au lieu de `text`) passait
le validateur mais compilait en asset VIDE (TTS sans texte), et inversement.

Règle « vide » : `None` et chaîne vide (après strip) comptent comme ABSENTS — ce
qui empêche aussi un `prompt=""`/`text=""` de passer pour présent.

Import-light : `registry` est sans dépendance lourde (cf. son module).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..features.compositing.registry import get_contract


def _keys(kind: str, field_name: str) -> Tuple[str, ...]:
    """Nom canonique + alias d'un champ du contrat (ou juste le nom si inconnu)."""
    for fld in get_contract(kind).fields:
        if fld.name == field_name:
            return (fld.name, *fld.aliases)
    return (field_name,)


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def field_value(params: Dict[str, Any], kind: str, field_name: str) -> Optional[Any]:
    """Première valeur non-vide parmi le nom canonique et ses alias, sinon None."""
    for key in _keys(kind, field_name):
        if key in params and not _is_empty(params[key]):
            return params[key]
    return None


def field_present(params: Dict[str, Any], kind: str, field_name: str) -> bool:
    """True si le champ (nom ou alias) porte une valeur non-vide."""
    return field_value(params, kind, field_name) is not None


def missing_required(params: Dict[str, Any], kind: str) -> List[str]:
    """Champs REQUIS du contrat absents (vide = complet), vide-conscient."""
    return [
        fld.name
        for fld in get_contract(kind).fields
        if fld.required and not field_present(params, kind, fld.name)
    ]
