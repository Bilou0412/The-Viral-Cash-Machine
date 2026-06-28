---
paths:
  - "tests/**"
---

# Tests — règles

- **Split cheap / heavy.** Par défaut la suite est rapide (~6 s) ; les tests lourds (rendu
  réel, etc.) ne tournent qu'avec `pytest --runheavy` (cf. `tests/conftest.py`). Marquer le
  lourd correctement plutôt que de ralentir la suite par défaut.
- **Golden tests.** Le rendu a une référence figée (`tests/fixtures/golden/`,
  `tests/golden_tools.py`, `tests/test_golden.py`). Régénérer la golden avec
  `tests/capture_golden.py` **seulement** sur changement intentionnel — sinon une diff
  golden = régression à investiguer.
- **Invariants du rail.** Couverture clé : `document_to_spec(adventure_to_bricks(s))` produit
  des assets génératifs **identiques** à `adventure_to_spec(s)` (rien perdu/ajouté). Ne pas
  casser ces invariants en touchant le rail briques.
- **Offline d'abord.** Privilégier des tests purs/hors-ligne (fakes : `resolve_fake`,
  `fake_adventure_decomposer`) ; pas d'appels réseau réels dans la suite rapide.
- **Commande** : `python -m pytest -q` (rapide) ; `python -m pytest -q --runheavy` (tout).
