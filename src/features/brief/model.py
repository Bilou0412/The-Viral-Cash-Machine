"""Modèle du Brief — le cahier des charges du producteur.

Le **Brief** est la première donnée de la chaîne : ce que le producteur veut
(objectif, audience, plateforme, durée, coût). Il oriente ensuite chaque
agent-métier (scénariste, DA, chef op…). Neutre, sans dépendance à
`studio`/`editor` (respect des couches : `features` ne dépend de rien de haut).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# Les plateformes court-format visées (9:16 vertical).
Platform = Literal["tiktok", "reels", "shorts", "youtube_short"]


class Brief(BaseModel):
    """Le cahier des charges d'une vidéo, tenu par le producteur.

    Les cinq champs demandés au producteur : **objectif, audience, plateforme,
    durée, coût**. `ton`/`langue`/`notes` sont *orientés* par l'agent producteur
    (proposés puis éditables) — ils existent pour que le décrypteur cesse de
    coder « français » / le ton en dur : une seule source de vérité.
    """

    model_config = ConfigDict(extra="ignore")

    # Les cinq champs du producteur.
    objectif: str = ""
    audience: str = ""
    plateforme: Platform = "tiktok"
    duree_s: float = 30.0
    budget_usd: float = 0.0  # plafond de coût ; 0 = non précisé

    # Orientés par l'agent producteur, éditables par l'utilisateur.
    ton: str = ""
    langue: str = "fr"
    notes: str = ""

    def orientation(self) -> str:
        """Résumé libre (ton + notes) à replier dans `style_identity` du décrypteur."""
        return " ".join(p for p in (self.ton.strip(), self.notes.strip()) if p)
