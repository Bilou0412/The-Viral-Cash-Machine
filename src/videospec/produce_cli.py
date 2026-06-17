"""CLI « prompt → vraie vidéo MP4 ».

Branche le RealAssetResolver (Replicate/Whisper) sur le MoviePyRenderEngine via
`produce()`. C'est le chemin RÉEL : il génère et télécharge de vrais assets, puis
monte le MP4 — exactement la même chaîne que les tests offline, seul le resolver
change.

Usage (dans le conteneur, avec les clés) :

    REPLICATE_API_TOKEN=... [OPENAI_API_KEY=...] \
      python -m src.videospec.produce_cli \
        --prompt "une nuit dans un dirigeable abandonné" \
        --n-rounds 1 --draft --out exports/story.mp4

Par défaut : 1 scène de choix, vidéos en `--draft` (moins cher/rapide), script
« fake » (histoire canon, ne nécessite QUE REPLICATE_API_TOKEN). `--script openai`
génère le script depuis le prompt (nécessite OPENAI_API_KEY + --left/--right).
"""

from __future__ import annotations

import argparse
import os
import sys

from .models import VideoSpec
from .produce import produce
from .render_moviepy import MoviePyRenderEngine
from .resolve_real import RealAssetResolver


def _build_spec(args: argparse.Namespace) -> VideoSpec:
    from ..features.scripting.adventure_to_spec import adventure_to_spec
    from ..features.scripting.themes import get_theme

    theme = get_theme(args.theme)

    if args.script == "openai":
        from openai import OpenAI

        from ..features.scripting.openai_adventure_decomposer import (
            OpenAIAdventureDecomposer,
        )

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = args.model or os.getenv("VCM_OPENAI_MODEL", "gpt-4o-mini")
        decomposer = OpenAIAdventureDecomposer(client, model)
        script = decomposer.decompose_adventure(
            args.prompt,
            char_left_name=args.left,
            char_right_name=args.right,
            n_rounds=args.n_rounds,
        )
    else:
        from ..features.scripting.fake_adventure_decomposer import (
            FakeAdventureDecomposer,
        )

        script = FakeAdventureDecomposer().decompose_adventure(
            args.prompt,
            char_left_name=args.left,
            char_right_name=args.right,
            n_rounds=args.n_rounds,
        )

    return adventure_to_spec(script, theme=theme, side=args.side)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="prompt → vraie vidéo MP4 (histoire à choix)")
    p.add_argument("--prompt", required=True, help="pitch de l'histoire (horreur)")
    p.add_argument("--out", default="exports/story.mp4", help="chemin du MP4 final")
    p.add_argument(
        "--project-dir",
        default="exports/real_assets",
        help="dossier où télécharger les assets générés",
    )
    p.add_argument("--n-rounds", type=int, default=1, help="nombre de scènes de choix")
    p.add_argument("--theme", default="horror", help="thème (DA en cascade)")
    p.add_argument("--side", default="left", choices=["left", "right"])
    p.add_argument("--left", default="Étienne", help="prénom perso gauche")
    p.add_argument("--right", default="Marc", help="prénom perso droite")
    p.add_argument(
        "--script",
        default="fake",
        choices=["fake", "openai"],
        help="source du script (fake = canon, openai = depuis le prompt)",
    )
    p.add_argument("--model", default=None, help="modèle OpenAI (si --script openai)")
    p.add_argument(
        "--draft",
        action="store_true",
        help="vidéos en mode draft (moins cher / plus rapide)",
    )
    args = p.parse_args(argv)

    if not os.getenv("REPLICATE_API_TOKEN"):
        print("❌ REPLICATE_API_TOKEN absent — impossible de générer en réel.", file=sys.stderr)
        return 2

    print(f"▶ Construction du spec ({args.script}, n_rounds={args.n_rounds})…")
    spec = _build_spec(args)
    print(f"  {len(spec.assets)} assets, {len(spec.segments)} segments à produire.")

    resolver = RealAssetResolver(draft=args.draft)
    engine = MoviePyRenderEngine()
    out = produce(spec, args.project_dir, resolver, engine, args.out)
    print(f"✅ Vidéo produite : {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
