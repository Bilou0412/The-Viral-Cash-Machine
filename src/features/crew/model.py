"""Modèles de l'équipe (crew) — les artefacts que produisent les agents-métiers.

Pour l'instant : le **kit de distribution** (ce que produit l'attaché de presse /
Growth). Neutre, sans dépendance à l'éditeur (respect des couches : `features`
ne dépend pas de `studio`/`editor`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DistributionKit(BaseModel):
    """La fiche de sortie d'une vidéo, écrite par l'attaché de presse / Growth.

    Titre accrocheur, description, hashtags et hook (première phrase qui retient).
    """

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    hook: str = ""
