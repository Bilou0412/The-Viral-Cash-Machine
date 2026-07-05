"""produce — orchestrateur du chemin « prompt → MP4 » (SPEC §5).

Deux fonctions minces, le siège où l'on branche resolver/engine réels ou
factices :

- `produce(spec, ...)`        : resolve puis render d'un VideoSpec déjà construit.
- `produce_from_prompt(...)`  : prompt → décomposeur → adventure_to_spec → produce.

Module mince et sans import lourd au niveau racine : les implémentations lourdes
(MoviePyRenderEngine / FakeAssetResolver) sont injectées par l'appelant, ce qui
garde ce module testable et le bascule réel/factice trivial.
"""

from __future__ import annotations

from typing import Protocol

from .models import Canvas, VideoSpec
from .ports import AssetResolver, RenderEngine


class _AdventureDecomposer(Protocol):
    def decompose_adventure(
        self,
        prompt: str,
        char_left_name: str = ...,
        char_right_name: str = ...,
        char_left_desc: str = ...,
        char_right_desc: str = ...,
        n_rounds: int = ...,
    ) -> object: ...


def produce(
    spec: VideoSpec,
    project_dir: str,
    resolver: AssetResolver,
    engine: RenderEngine,
    output_path: str,
) -> str:
    """Résout tous les assets du `spec` puis rend le MP4. Retourne le chemin."""
    resolved = resolver.resolve(spec, project_dir)
    return engine.render(spec, resolved, output_path)


def produce_from_prompt(
    prompt: str,
    decomposer: _AdventureDecomposer,
    resolver: AssetResolver,
    engine: RenderEngine,
    project_dir: str,
    output_path: str,
    *,
    theme: object = None,
    side: str = "left",
    n_rounds: int | None = None,
    canvas: Canvas | None = None,
) -> str:
    """prompt → AdventureScript → VideoSpec → MP4.

    `canvas` (optionnel) surcharge le canvas du spec (utile pour rendre petit/vite
    en test). `theme`/`side`/`n_rounds` sont passés tels quels au pipeline aventure.
    """
    # Import local : garde `videospec/__init__` léger et évite un cycle d'import.
    from ..features.scripting.adventure_to_spec import adventure_to_spec

    if n_rounds is None:
        script = decomposer.decompose_adventure(prompt)
    else:
        script = decomposer.decompose_adventure(prompt, n_rounds=n_rounds)
    spec = adventure_to_spec(script, theme=theme, side=side)  # type: ignore[arg-type]
    if canvas is not None:
        spec = spec.model_copy(update={"canvas": canvas})
    return produce(spec, project_dir, resolver, engine, output_path)
