# Harnais de vérification (AUTONOMY_PLAN V1) — pilotable par Claude.
# Tout tourne dans le conteneur de DEV (deps lourdes présentes, code monté en live),
# sauf le build front (Node sur l'hôte). `make verify` = la boucle complète.

DC := docker compose -f docker-compose.dev.yml
EXEC := $(DC) exec -T dev
# mypy : base de modules = /app uniquement (sinon src/ résolu sous deux noms).
MYPY := $(DC) exec -T -e PYTHONPATH=/app dev sh -c "cd /app && python -m mypy src"
# Baseline d'erreurs mypy (dette legacy : compositor/generation/overlays…).
# `verify` échoue si on DÉPASSE ce nombre (cliquet : à faire baisser, jamais monter).
MYPY_BASELINE := 40

.PHONY: help dev-up dev-down sh test typecheck lint build-front verify e2e

help:
	@echo "make dev-up      # démarre le conteneur de dev (build si besoin)"
	@echo "make test        # pytest (suite complète, dans le conteneur)"
	@echo "make typecheck   # mypy src (rapport complet)"
	@echo "make lint        # ruff"
	@echo "make build-front # build du front (tsc + vite, sur l'hôte)"
	@echo "make verify      # dev-up + mypy(cliquet) + pytest + build-front"
	@echo "make e2e         # tests navigateur Playwright (front mock, sur l'hôte)"

dev-up:
	$(DC) up -d --build

dev-down:
	$(DC) down

sh: dev-up
	$(DC) exec dev bash

test: dev-up
	$(EXEC) python -m pytest -q

typecheck: dev-up
	$(MYPY) || true

lint: dev-up
	$(EXEC) ruff check src tests || true

build-front:
	cd frontend && npm run build

# Boucle de vérification. pytest + build = portes dures ; mypy = cliquet baseline.
verify: dev-up
	@echo "── mypy (cliquet, baseline $(MYPY_BASELINE)) ─────────────────"
	@n=$$($(MYPY) 2>&1 | grep -c 'error:' || true); \
	  echo "mypy: $$n erreur(s) (baseline $(MYPY_BASELINE))"; \
	  if [ "$$n" -gt "$(MYPY_BASELINE)" ]; then \
	    echo "❌ mypy: régression ($$n > $(MYPY_BASELINE))"; \
	    $(MYPY) 2>&1 | grep 'error:' | tail -40; exit 1; \
	  fi
	@echo "── pytest ────────────────────────────────────────────"
	$(EXEC) python -m pytest -q
	@echo "── build front ───────────────────────────────────────"
	cd frontend && npm run build
	@echo "✅ verify OK"

# Tests E2E navigateur (AUTONOMY_PLAN V3) — Playwright pilote le front en mode
# mock (VITE_USE_MOCKS=true), aucun backend Python requis. Tourne sur l'HÔTE
# (Node), pas dans le conteneur de dev. Installe deps + chromium si absents.
# NB : volontairement HORS de `verify` pour l'instant.
e2e:
	cd e2e && [ -d node_modules ] || npm install
	cd e2e && npx playwright install chromium
	cd e2e && npm test
