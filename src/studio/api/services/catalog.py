"""Le CATALOGUE — la palette COMPLÈTE que les agents (et l'UI) peuvent voir.

La feature du projet, c'est de **co-construire des templates** : les agents doivent
donc VOIR tout ce qu'on sait faire. Ce module réunit les deux catalogues déclaratifs
existants en une seule vue machine-lisible :

- **génératif** : les contrats de capacité (`registry.CONTRACTS` : image/video/voice)
  → `ToolCard` (champs + modèles préférés) ;
- **montage** : la palette d'effets (`registry.REGISTRY`, kind ``montage`` : timer,
  choix, zoom, nameplate, face-cam, narration, eye-open) → `EffectCard` (nom + résumé).

Source unique de « ce qu'on peut assembler ». Pur, sans I/O — la route l'expose tel quel
(`GET /api/catalog`) et `assemble_context` en injecte la part utile à chaque agent.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....features.compositing.registry import CONTRACTS
from .context import EffectCard, ToolCard, _tool_card, effect_cards


class Catalog(BaseModel):
    """La palette complète : briques génératives + effets de montage."""

    generative: list[ToolCard] = Field(default_factory=list)
    effects: list[EffectCard] = Field(default_factory=list)


def build_catalog() -> Catalog:
    """Assemble le catalogue complet (tous les kinds génératifs + tous les effets)."""
    return Catalog(
        generative=[_tool_card(kind) for kind in CONTRACTS],
        effects=effect_cards(),
    )
