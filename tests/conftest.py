"""Config pytest partagée — allègement du coût des tests (étape T du plan briques).

Les tests LOURDS (vrai rendu MoviePy/ffmpeg, intégration FastAPI/DB) sont SKIPPÉS
par défaut pour que `pytest` reste rapide dans la boucle de dev (la couverture qui
compte au quotidien — génération de SCRIPT, modèles, compilateurs — est offline et
quasi gratuite). Pour tout lancer :

    pytest --runheavy            # tout, y compris render + intégration lente

Marqueurs :
- `render` : exécute un vrai rendu MoviePy/ffmpeg (CPU, lent).
- `slow`   : intégration lourde (TestClient FastAPI + SQLite), sans réseau.

Note : les tests golden de RÉGRESSION (SSIM ffmpeg) ne tournent déjà que si
`GOLDEN_CANDIDATE` est défini ; ils n'alourdissent pas le run par défaut.
"""

import pytest

_HEAVY_MARKS = ("render", "slow")


def pytest_addoption(parser):
    parser.addoption(
        "--runheavy",
        action="store_true",
        default=False,
        help="exécuter aussi les tests lourds (render MoviePy + intégration lente)",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "render: vrai rendu MoviePy/ffmpeg (lent, CPU)")
    config.addinivalue_line("markers", "slow: intégration lourde (FastAPI/DB), hors-ligne")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runheavy"):
        return
    skip_heavy = pytest.mark.skip(reason="test lourd — passe --runheavy pour l'exécuter")
    for item in items:
        if any(mark in item.keywords for mark in _HEAVY_MARKS):
            item.add_marker(skip_heavy)
