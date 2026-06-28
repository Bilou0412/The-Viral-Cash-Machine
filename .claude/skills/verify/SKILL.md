---
name: verify
description: Lancer la boucle de vérification (mypy cliquet + pytest + build front) et résumer pass/fail. Utilise make verify si Docker est dispo, sinon le chemin natif.
---

# /verify — boucle de vérification

But : confirmer qu'on n'a rien cassé, de façon déterministe.

## Choix du chemin

1. **Docker dispo** (`docker compose` présent et utilisable) → `make verify` :
   mypy (cliquet, **baseline 40** — échoue si on dépasse) + `pytest` + build front.
   `make e2e` pour les tests navigateur Playwright (optionnel, hors `verify`).
2. **Sinon (conteneur web, pas de Docker)** → chemin natif :
   ```bash
   pip install -q -r requirements.txt -r requirements-dev.txt   # si pas déjà fait
   python -m mypy src              # compter les erreurs, comparer à la baseline 40
   python -m pytest -q             # rapide (~6 s) ; --runheavy si rendu touché
   cd frontend && npm run build    # si le front a changé
   ```

## Rapport attendu
- Nombre d'erreurs mypy vs baseline 40 (régression si > 40).
- Résultat pytest (passed/failed ; nommer les tests rouges).
- Build front OK/KO si lancé.
- Conclusion nette : **vert** (rien cassé) ou **liste précise** de ce qui casse.
