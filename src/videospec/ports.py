"""Ports du studio : résolution d'assets et moteur de rendu.

Le RenderEngine est interchangeable (MoviePy aujourd'hui, Remotion/Revideo
demain) : il ne voit que le VideoSpec et des assets déjà résolus sur disque.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .models import VideoSpec


@dataclass(frozen=True)
class ResolvedAssets:
    """Sortie de la phase resolve : tout ce dont le rendu a besoin, sur disque.

    - paths : asset id -> chemin local du fichier généré/téléchargé
    - heads : positions normalisées des têtes détectées (pour les HeadAnchor)
    - transcripts : asset id audio -> mots horodatés [{text, start, end}, ...]
    """

    paths: Mapping[str, str]
    heads: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    transcripts: Mapping[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)


class AssetResolver(Protocol):
    """Phase « apply » : génère/télécharge tous les assets déclarés du spec."""

    def resolve(self, spec: VideoSpec, project_dir: str) -> ResolvedAssets:
        ...


class RenderEngine(Protocol):
    """Interprète un VideoSpec résolu et produit le fichier vidéo final."""

    def render(
        self, spec: VideoSpec, resolved: ResolvedAssets, output_path: str
    ) -> str:
        ...
