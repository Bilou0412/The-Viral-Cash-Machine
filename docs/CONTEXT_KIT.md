# Repo Context Kit — version adaptée à VCM

Le kit d'origine (générique) garde le contexte d'un repo propre **tout seul** via des
hooks Claude Code : état auto-mis-à-jour, code mort refusé, plans testables, direction
unique. Il a été **adapté** ici pour épouser le rail existant de The-Viral-Cash-Machine
(cf. `CLAUDE.md`, `.claude/rules/architecture.md`) **sans dupliquer** ce qui existe déjà.

## Ce qui a été installé (adapté)

| Composant | Rôle | Adaptation |
|---|---|---|
| `scripts/refresh_state.py` | Génère `.claude/state/STATE.md` + `MAP.md` (santé mécanique : modules `src/`, tests, code mort, git) | Scanne `src/`, points d'entrée réels (`studio/api/app.py`, `pipeline.py`, `app.py`) |
| `scripts/check_dead_code.py` | Détecte le code mort (`make dead`) | `vulture` sur `src`+`scripts` (min-confidence 90, `app.py` legacy exclu), knip front si présent. **Indicatif**, non bloquant |
| `scripts/new_plan.py` | `make plan name="..."` → plan testable + stub de test | Marqueurs `@pytest.mark.render`/`slow` + `--runheavy` (pas `real`) ; pointe vers `ROADMAP.md` et `docs/DECISIONS.md` |
| `.claude/hooks/inject_context.py` | Injecte STATE + pointeur direction au démarrage/reprise de session | Ajouté aux hooks `SessionStart` existants (startup + resume), sans les remplacer |
| `.claude/hooks/_common.py` | Helpers hooks | — |
| `scripts/stop_verify.sh` | Hook `Stop` **non bloquant** existant | Enrichi : rafraîchit l'état + signale le code mort (reste non bloquant, choix du repo) |

## Décisions d'adaptation (pourquoi le kit n'est pas copié tel quel)

Les règles du repo (« un seul rail », pas de 2ᵉ système parallèle) interdisent une
installation à l'identique. Écartés volontairement :

- **`backend/llm/` (client OpenAI unique du kit)** → le repo a déjà des **ports
  `typing.Protocol` + impls fake/réelle par feature** (`src/features/*/ports.py`). Ajouter
  un client global serait un 2ᵉ système LLM (anti-pattern).
- **`docs/DIRECTION.md` + `BACKLOG.md` + `make direction`** → la **source unique de
  direction est `ROADMAP.md`** (§4 état / §5 étapes). Les décisions vont dans
  `docs/DECISIONS.md`. STATE.md ne décrit que la santé **mécanique**, jamais le cap.
- **Gate `Stop` bloquant (exit 2) du kit** → le repo a fait le choix d'un `Stop`
  **advisory** (`verify.sh --fast` en contexte). On respecte ce choix ; le kit y ajoute
  juste le rafraîchissement d'état et le signal de code mort.
- **Tests `--run-real`** → convention du repo = **`--runheavy`** (`tests/conftest.py`).

## Usage

```bash
make state                 # régénère l'état (aussi fait au démarrage de session)
make dead                  # inventaire du code mort (indicatif)
make plan name="ma tache"  # nouveau plan testable + stub
```

Prérequis dev : `vulture` (ajouté à `requirements-dev.txt`). La vérification reste
`bash scripts/verify.sh` (mypy strict + ruff + pytest + build front), inchangée.
