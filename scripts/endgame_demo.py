#!/usr/bin/env python
"""Démonstration de la BOUCLE ENDGAME EN ENTIER, en une commande — texte + données seulement.

`idée → moule → 3 variantes → prédiction → [gagnante] → appliquée au doc → publiée →
perfs réelles → recalibration → le classement CHANGE`. Aucune génération d'image/vidéo :
tout est en Fakes déterministes (offline, gratuit, reproductible). Prouve que la boucle
se FERME et que le moat apprend (les perfs réelles inversent l'a priori).

    python scripts/endgame_demo.py "une barista rate puis réussit son latte art"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.features.virality import apply_hook_to_document, rank_hooks  # noqa: E402
from src.studio.api.services.formats import build_format_document  # noqa: E402
from src.studio.api.services.performance import calibrated_predictor  # noqa: E402
from src.studio.api.services.publish import publish_video  # noqa: E402
from src.studio.api.services.virality import get_hook_generator, propose_hooks  # noqa: E402


def _rule(title: str) -> None:
    print(f"\n{'─' * 66}\n{title}\n{'─' * 66}")


def demo(idea: str) -> int:
    # 1. IDÉE → MOULE → document (texte). Offline = Fake (aucune image générée).
    _rule("1. IDÉE → MOULE (format « scenes ») → document")
    doc = build_format_document("scenes", idea, openai_key=None, options={"n_scenes": 1})
    print(f"   document : {len([b for b in doc.bricks])} briques · {len(doc.scenes)} scène(s)")

    # 2. → 3 VARIANTES DE HOOK → PRÉDICTION (a priori) → CLASSEMENT
    _rule("2. → 3 VARIANTES → PRÉDICTION (a priori) → CLASSEMENT")
    ranked = propose_hooks(idea, n_variants=3, openai_key=None)
    for i, sv in enumerate(ranked.variants):
        mark = "★" if i == 0 else " "
        print(f"   {mark} {sv.score.overall:>5.1f}  [{sv.variant.angle}]  {sv.variant.hook_text}")
    winner = ranked.winner
    assert winner is not None
    print(f"   → GAGNANTE (a priori) : « {winner.variant.angle} »")

    # 3. L'HUMAIN APPROUVE → on applique la gagnante à l'ouverture du doc
    _rule("3. [humain approuve] → APPLIQUE la gagnante à la 1re image du doc")
    applied = apply_hook_to_document(doc, winner.variant)
    print(f"   appliqué : {applied}  → 1re brique image = « {doc.bricks[0].image.params.get('prompt', '')[:70]}… »")

    # 4. → PUBLICATION (simulée — aucun post réel)
    _rule("4. → PUBLICATION (simulée)")
    pub = publish_video("/exports/demo.mp4", platform="tiktok", caption=winner.variant.hook_text)
    print(f"   {pub.status} · id={pub.published_id} · {pub.url}")

    # 5. → PERFS RÉELLES → RECALIBRATION → le classement suit la RÉALITÉ (le moat)
    _rule("5. → PERFS RÉELLES → RECALIBRATION (le moat) → nouveau classement")
    all_variants = get_hook_generator(None).generate_hooks(idea, n=5)  # tous les angles
    published = [(f"pub_{v.angle}", v.angle) for v in all_variants]     # « déjà publiés »
    learned = calibrated_predictor(published)                          # perfs réelles → poids appris
    relearned = rank_hooks(all_variants, learned)
    for i, sv in enumerate(relearned.variants):
        mark = "★" if i == 0 else " "
        print(f"   {mark} {sv.score.overall:>5.1f}  [{sv.variant.angle}]")
    new_winner = relearned.winner
    assert new_winner is not None
    print(f"   → GAGNANTE (APPRISE des perfs) : « {new_winner.variant.angle} »")

    _rule("BILAN")
    changed = new_winner.variant.angle != winner.variant.angle
    print(f"   a priori : « {winner.variant.angle} »  →  appris : « {new_winner.variant.angle} »")
    print("   ✅ la boucle se ferme ET le moat APPREND (les perfs réelles ont changé le choix)."
          if changed else
          "   (a priori == appris cette fois — la donnée confirmait déjà le choix)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    idea = args[0] if args else "une barista rate puis réussit son latte art"
    print(f"ENDGAME (offline, Fakes — zéro génération d'image) — « {idea} »")
    return demo(idea)


if __name__ == "__main__":
    raise SystemExit(main())
