#!/usr/bin/env python3
"""SessionStart — rafraîchit l'état mécanique puis l'injecte dans le contexte.

Le stdout (texte brut) est ajouté au contexte que Claude voit au démarrage/reprise
de session. On rafraîchit d'abord STATE.md/MAP.md (santé du repo), puis on imprime
un condensé + un POINTEUR vers ROADMAP.md (la source unique de direction — on ne la
recopie pas ici pour ne pas créer une 2ᵉ source). Sortie bornée, jamais bloquant.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import project_dir, run


def main() -> int:
    root = project_dir()

    # 1) régénère l'état mécanique (best-effort, silencieux)
    with contextlib.suppress(Exception):
        run(["python3", "scripts/refresh_state.py"], cwd=root, timeout=60)

    state_file = root / ".claude/state/STATE.md"
    if state_file.exists():
        print("# CONTEXTE REPO (injecté automatiquement)\n")
        print(state_file.read_text(encoding="utf-8"))

    # 2) pointeur direction — la SOURCE reste ROADMAP.md (§4 état, §5 étapes)
    print("\n## Direction (source unique = ROADMAP.md)\n")
    print(
        "Pour reprendre : lis `ROADMAP.md` §4 (déjà fait) puis §5 (étapes restantes) — "
        "première ligne ⬜ = prochaine étape. Une étape par session (protocole §7). "
        "Skill dédié : `/resume`."
    )
    print(
        "\n> Rappel : une seule direction (ROADMAP.md), un seul rail "
        "(`.claude/rules/architecture.md`). Commandes du kit : `make plan` / `make dead` / `make state`."
    )
    return 0


if __name__ == "__main__":
    # jamais bloquant : toute exception = exit 0
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0) from None
