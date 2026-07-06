"""Ports de l'équipe (crew) — un agent-métier = un `Protocol`.

Chaque métier du studio est un agent qui prend un contexte et produit son
artefact. Premier agent : l'attaché de presse / Growth (kit de distribution).
Les impls (Fake déterministe, OpenAI réel) sont injectées au bord (mirror du
décrypteur de scènes).
"""

from __future__ import annotations

from typing import Protocol

from .model import ArtDirection, DistributionKit, SceneRef


class CrewAgentError(ValueError):
    """Un agent-métier n'a pas pu produire un artefact exploitable.

    Levé quand la réponse IA est vide/illisible : mieux vaut une erreur claire
    remontée au producteur qu'un artefact vide généré silencieusement.
    """


class DistributionAgent(Protocol):
    """L'attaché de presse / Growth : écrit la fiche de sortie d'une vidéo."""

    def write_kit(
        self, *, title: str, synopsis: str, narration: str = ""
    ) -> DistributionKit:
        """Contexte de la vidéo → `DistributionKit` (titre, description, hashtags, hook)."""
        ...


class ArtDirectionAgent(Protocol):
    """Le directeur artistique : réécrit l'identité visuelle (décors + art direction)."""

    def direct(
        self,
        *,
        tone: str,
        platform: str,
        language: str,
        art_direction: str,
        scenes: list[SceneRef],
    ) -> ArtDirection:
        """Brief (ton/plateforme) + scènes → `ArtDirection` (prompts image EN réécrits)."""
        ...
