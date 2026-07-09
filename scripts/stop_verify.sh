#!/usr/bin/env bash
# Hook `Stop` (indicatif, NON bloquant). Si du code a changé pendant le tour,
# lance `verify.sh --fast` (mypy cliquet + pytest rapide) et renvoie le résultat
# en contexte pour que l'agent corrige avant de rendre la main. Toujours exit 0.
# Silencieux sur les tours « doc-only » (aucun .py/.ts/.tsx touché).

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}" || exit 0

FILES=$({ git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2>/dev/null)
printf '%s\n' "$FILES" | grep -qE '^(src|tests)/.*\.py$|^(frontend|e2e)/.*\.(ts|tsx)$' || exit 0

OUT=$(bash scripts/verify.sh --fast 2>&1)
SUMMARY=$(printf '%s\n' "$OUT" | sed -n '/VERIFY/,$p')
[ -z "$SUMMARY" ] && SUMMARY=$(printf '%s\n' "$OUT" | tail -8)

# repo-context-kit : garder le contexte propre tout seul (indicatif, non bloquant).
# Rafraîchit l'état mécanique + compte le code mort (vulture) pour le signaler.
python3 scripts/refresh_state.py >/dev/null 2>&1 || true
DEAD=$(python3 scripts/check_dead_code.py --count 2>/dev/null | tail -1)
[ -z "$DEAD" ] && DEAD="?"

python3 - "$SUMMARY" "$DEAD" <<'PY'
import json, sys
summary, dead = sys.argv[1], sys.argv[2]
ctx = "[auto-verify --fast — du code a changé ce tour]\n" + summary
ctx += f"\n\n[code mort (vulture, indicatif) : {dead}] — détail : `make dead` (Loi 1 : supprimer le mort dans le même commit)."
print(json.dumps({"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": ctx}}))
PY
exit 0
