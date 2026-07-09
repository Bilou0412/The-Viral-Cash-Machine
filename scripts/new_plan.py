#!/usr/bin/env python3
"""Crée un plan testable-par-construction (repo-context-kit, adapté VCM).

Usage : python3 scripts/new_plan.py "nom-de-la-tache"
Génère docs/plans/<date>-<slug>.md + un stub de test tests/test_<slug>.py.
Le plan a une section « Tests d'abord » à remplir AVANT d'écrire le code.

Conventions du repo (cf. tests/conftest.py) : tests offline par défaut (fake
providers), tests lourds marqués `@pytest.mark.render` / `@pytest.mark.slow` et
lancés avec `--runheavy`. Pas de marqueur `real` ici : la vraie API OpenAI/
Replicate se teste via les impls réelles derrière les ports, pas dans la boucle.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "plan"


PLAN_TMPL = """# Plan — {title}

- Date : {date}
- Étape ROADMAP servie : _(colle l'ID/§ de ROADMAP.md §5 ; si ça ne sert pas une
  étape active, ça va dans le backlog de ROADMAP.md, pas ici)_

## Objectif
_(une phrase : quel comportement observable on ajoute/change)_

## Tests d'abord (OBLIGATOIRE avant tout code)
- [ ] Cas offline (fake provider) : _(entrée -> sortie attendue, déterministe)_
- [ ] Cas offline d'erreur : _(entrée invalide -> comportement attendu)_
- [ ] Cas lourd `@pytest.mark.render`/`slow` : _(seulement si render MoviePy ou
      intégration FastAPI/DB ; lancé avec `--runheavy`)_

Stub généré : `tests/{test_file}`

## Impact sur l'architecture (le « rail unique »)
- Modules touchés (`src/...`) :
- Nouveaux modules :
- Ports/impl fake+réelle concernés :
- Ce qui devient mort et sera supprimé dans ce changement :

## Definition of Done
- [ ] `bash scripts/verify.sh` vert (mypy strict + ruff + pytest + build front)
- [ ] tests lourds verts si concernés (`--runheavy`)
- [ ] `make dead` = zéro nouveau code mort
- [ ] décision d'archi notée dans `docs/DECISIONS.md` si structurelle
"""

TEST_TMPL = '''"""Tests pour : {title}. Écris-les AVANT le code (ils doivent échouer d'abord)."""
import pytest


def test_{fn}_offline():
    """Cas nominal, offline (fake provider derrière le port)."""
    pytest.fail("à implémenter : cas nominal offline")


@pytest.mark.slow
def test_{fn}_heavy():
    """Cas lourd (render MoviePy / intégration FastAPI+DB) ; lancé avec --runheavy."""
    pytest.fail("à implémenter : validation lourde (ou supprimer si non concerné)")
'''


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Usage : python3 scripts/new_plan.py "nom de la tache"')
        return 1
    title = sys.argv[1]
    slug = slugify(title)
    date = dt.date.today().isoformat()
    fn = slug.replace("-", "_")

    test_file = f"test_{fn}.py"
    test_path = ROOT / "tests" / test_file
    if test_path.exists():
        print(f"⚠️  {test_path.relative_to(ROOT)} existe déjà — non écrasé.")
    else:
        test_path.write_text(TEST_TMPL.format(title=title, fn=fn), encoding="utf-8")

    plan_dir = ROOT / "docs" / "plans"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"{date}-{slug}.md"
    plan_path.write_text(
        PLAN_TMPL.format(title=title, date=date, test_file=test_file), encoding="utf-8"
    )

    print(f"Plan créé      : {plan_path.relative_to(ROOT)}")
    print(f"Stub de test   : tests/{test_file}")
    print("→ Remplis « Tests d'abord », écris les tests, PUIS le code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
