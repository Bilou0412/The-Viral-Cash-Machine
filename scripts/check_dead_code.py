#!/usr/bin/env python3
"""Détecte le code mort (repo-context-kit, adapté VCM). ADVISORY par défaut.

- Python : `vulture` sur `src` + `scripts` (fonctions/imports/variables non
  utilisés). `src/app.py` (monolithe Streamlit legacy) est exclu, comme il l'est
  déjà du typage strict mypy et du lint ruff (cf. pyproject.toml).
- Front   : `knip` si `frontend/` en est équipé (sinon ignoré silencieusement).

La grosse base (FastAPI, ports dynamiques) génère des faux positifs : ce script
est INDICATIF (le hook Stop le rapporte, il ne bloque pas). Pour l'inventaire
détaillé : `make dead`.

Options :
    --count   : imprime juste le nombre d'éléments morts (pour STATE.md)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# min_confidence 90 = très peu de faux positifs. On exclut le legacy Streamlit.
VULTURE_CMD = [
    "vulture",
    "src",
    "scripts",
    "--min-confidence",
    "90",
    "--exclude",
    "*/app.py",
]


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)


def python_dead() -> tuple[int, str]:
    try:
        r = run(VULTURE_CMD)
    except FileNotFoundError:
        return 0, "(vulture non installé : pip install -r requirements-dev.txt)"
    # vulture renvoie 3 quand il trouve du code mort, 0 sinon.
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return len(lines), "\n".join(lines)


def front_dead() -> tuple[int, str]:
    pkg = ROOT / "frontend" / "package.json"
    if not pkg.exists() or "knip" not in pkg.read_text(encoding="utf-8"):
        return 0, ""  # front non équipé de knip → ignoré
    try:
        r = run(["npx", "--no-install", "knip", "--no-progress"])
    except FileNotFoundError:
        return 0, ""
    if r.returncode == 0:
        return 0, ""
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    return len(lines), "\n".join(lines[:40])


def main() -> int:
    py_n, py_txt = python_dead()
    fe_n, fe_txt = front_dead()
    total = py_n + fe_n

    if "--count" in sys.argv:
        print(total)
        return 0

    if total == 0:
        print("Zéro code mort détecté (vulture --min-confidence 90). 👍")
        return 0

    print(f"Code mort détecté (indicatif) : {total} élément(s).\n")
    if py_txt:
        print("--- Python (vulture) ---")
        print(py_txt)
    if fe_txt:
        print("\n--- Front (knip) ---")
        print(fe_txt)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
