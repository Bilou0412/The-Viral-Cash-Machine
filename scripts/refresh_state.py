#!/usr/bin/env python3
"""Régénère `.claude/state/STATE.md` + `MAP.md` à partir de la réalité du repo.

C'est le cœur du « contexte auto-mis-à-jour » : un scan factuel de `src/`, pas
une prose figée à la main. Lancé par le hook SessionStart et par `make state`.
NB : la direction produit reste dans ROADMAP.md (source unique) — STATE.md ne
décrit que la SANTÉ mécanique (modules, tests, code mort, git), pas le cap.
"""
from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".claude" / "state"
STATE.mkdir(parents=True, exist_ok=True)

IGNORE = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".claude"}
# Points d'entrée réels du rail (cf. CLAUDE.md).
ENTRY_POINTS = [
    "src/studio/api/app.py",  # backend FastAPI (produit)
    "src/pipeline.py",  # séquence pure
    "src/app.py",  # legacy Streamlit (en retrait)
]


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, timeout=60
        ).stdout.strip()
    except Exception:
        return ""


def src_modules() -> list[Path]:
    return sorted(
        p.relative_to(ROOT)
        for p in (ROOT / "src").rglob("*.py")
        if not any(part in IGNORE for part in p.parts)
    )


def test_count() -> int:
    tdir = ROOT / "tests"
    if not tdir.exists():
        return 0
    return sum(1 for p in tdir.rglob("test_*.py"))


def dead_code_count() -> str:
    try:
        r = subprocess.run(
            ["python3", "scripts/check_dead_code.py", "--count"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return r.stdout.strip() or "0"
    except Exception:
        return "inconnu"


def main() -> int:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    mods = src_modules()
    n_tests = test_count()

    # --- STATE.md ---------------------------------------------------------
    state = [
        f"# État du repo — généré le {now}",
        "",
        "> Fichier GÉNÉRÉ par `scripts/refresh_state.py`. Ne pas éditer à la main.",
        "> La DIRECTION produit vit dans `ROADMAP.md` (§4 état, §5 étapes), pas ici.",
        "",
        "## Santé mécanique",
        f"- Modules Python (`src/`) : **{len(mods)}**",
        f"- Fichiers de test (`tests/`) : **{n_tests}**",
        f"- Code mort (vulture, indicatif) : **{dead_code_count()}** élément(s)",
        f"- Branche : {sh(['git', 'branch', '--show-current']) or '—'}",
        f"- Dernier commit : {sh(['git', 'log', '-1', '--oneline']) or '—'}",
        "",
        "## Points d'entrée du rail",
    ]
    for e in ENTRY_POINTS:
        exists = "✅" if (ROOT / e).exists() else "❌ (absent)"
        state.append(f"- `{e}` {exists}")
    state += [
        "",
        "## Fichiers modifiés non commités",
        "```",
        sh(["git", "status", "--short"]) or "(rien)",
        "```",
        "",
        "> Vérif complète : `bash scripts/verify.sh` — code mort détaillé : `make dead`.",
    ]
    (STATE / "STATE.md").write_text("\n".join(state) + "\n", encoding="utf-8")

    # --- MAP.md : arbre des modules src/ ---------------------------------
    tree = [f"# Carte des modules `src/` — généré le {now}", ""]
    by_dir: dict[str, list[str]] = {}
    for m in mods:
        d = str(m.parent)
        by_dir.setdefault(d, []).append(m.name)
    for d in sorted(by_dir):
        tree.append(f"## {d}")
        tree += [f"- {f}" for f in sorted(by_dir[d])]
        tree.append("")
    (STATE / "MAP.md").write_text("\n".join(tree) + "\n", encoding="utf-8")

    print(f"État régénéré : {len(mods)} modules src/, {n_tests} fichiers de test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
