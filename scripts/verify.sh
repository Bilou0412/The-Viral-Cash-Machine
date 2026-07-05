#!/usr/bin/env bash
# Harnais de vérification NATIF (zéro Docker) — source unique utilisée par la CI,
# le hook de session (.claude/settings.json) et les skills /verify et /ship.
# Reproduit `make verify` sans le conteneur Docker. Rapport compact PASS/FAIL.
#
# Usage :
#   scripts/verify.sh                 # mypy(cliquet) + pytest rapide + build front
#   scripts/verify.sh --fast          # mypy + pytest rapide seulement (hook de session)
#   scripts/verify.sh --heavy         # pytest complet (--runheavy)
#   scripts/verify.sh --no-front      # sauter le build front
#   scripts/verify.sh --e2e           # + tests navigateur Playwright (front en mock)
#
# mypy est STRICT et à ZÉRO erreur (rigueur type-Rust). Le cliquet reste en place
# comme garde-fou, mais la baseline est 0 : toute nouvelle erreur casse le build.
MYPY_BASELINE="${MYPY_BASELINE:-0}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

FAST=0; HEAVY=0; NO_FRONT=0; E2E=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --heavy) HEAVY=1 ;;
    --no-front) NO_FRONT=1 ;;
    --e2e) E2E=1 ;;
    *) echo "verify.sh: option inconnue: $arg" >&2; exit 2 ;;
  esac
done

PY="${PYTHON:-python}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

fail=0
summary=""
add() { summary="${summary}\n  $1"; }

# ── 1. mypy (cliquet baseline) ───────────────────────────────────────────
echo "── mypy (cliquet, baseline ${MYPY_BASELINE}) ───────────────────────"
mypy_out="$("$PY" -m mypy src 2>&1)"
n_err="$(printf '%s\n' "$mypy_out" | grep -c 'error:')"
echo "mypy: ${n_err} erreur(s) (baseline ${MYPY_BASELINE})"
if [ "$n_err" -gt "$MYPY_BASELINE" ]; then
  printf '%s\n' "$mypy_out" | grep 'error:' | tail -30
  add "❌ mypy : régression (${n_err} > ${MYPY_BASELINE})"; fail=1
else
  add "✅ mypy : ${n_err}/${MYPY_BASELINE}"
fi

# ── 1b. ruff (lint dur du code actif ; src/app.py legacy exclu via pyproject) ──
echo "── ruff (lint) ────────────────────────────────────────────────"
if "$PY" -m ruff check src tests; then add "✅ ruff"; else add "❌ ruff"; fail=1; fi

# ── 2. pytest ────────────────────────────────────────────────────────────
if [ "$HEAVY" -eq 1 ]; then
  echo "── pytest --runheavy ──────────────────────────────────────────"
  if "$PY" -m pytest -q --runheavy; then add "✅ pytest (complet)"; else add "❌ pytest (complet)"; fail=1; fi
else
  echo "── pytest (rapide) ────────────────────────────────────────────"
  if "$PY" -m pytest -q; then add "✅ pytest (rapide)"; else add "❌ pytest (rapide)"; fail=1; fi
fi

# ── 3. build front (sauf --fast / --no-front) ────────────────────────────
if [ "$FAST" -eq 0 ] && [ "$NO_FRONT" -eq 0 ]; then
  echo "── build front (tsc + vite) ───────────────────────────────────"
  if command -v npm >/dev/null 2>&1; then
    if ( cd frontend && npm run build ); then add "✅ build front"; else add "❌ build front"; fail=1; fi
  else
    add "⏭️  build front : npm absent (sauté)"
  fi
fi

# ── 4. e2e Playwright (seulement si --e2e) ───────────────────────────────
if [ "$E2E" -eq 1 ]; then
  echo "── e2e Playwright (front en mock) ─────────────────────────────"
  if command -v npm >/dev/null 2>&1; then
    if ( cd e2e && npm test ); then add "✅ e2e"; else add "❌ e2e"; fail=1; fi
  else
    add "⏭️  e2e : npm absent (sauté)"
  fi
fi

echo
echo "════════════ VERIFY ════════════"
printf '%b\n' "$summary"
if [ "$fail" -eq 0 ]; then echo "RÉSULTAT : ✅ PASS"; else echo "RÉSULTAT : ❌ FAIL"; fi
exit "$fail"
