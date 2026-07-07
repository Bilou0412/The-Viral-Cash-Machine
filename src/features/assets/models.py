"""Slugs de modèles Replicate — **source unique de vérité**.

Les identifiants envoyés à Replicate (image / vidéo i2v / voix). Ils étaient
dupliqués dans `services/pricing.py`, `replicate_provider.py` et
`scene_plan_to_document.py` → dérive garantie. On les centralise ici.

⚠️ Ces slugs ne sont PAS vérifiés automatiquement contre Replicate : un slug
périmé = 404 au 1er appel réel. Vérifie-les avec `scripts/dogfood_editor.py --check`
(qui fait `replicate.models.get(slug)` avec ton token, sans rien dépenser). Pour
corriger sans toucher au code (ou pendant un dogfood), surcharge par variable
d'env — utile tant que le bon slug n'est pas figé.

Note : `registry.py` liste `minimax/speech-02-turbo` en slot low-cost, alors que le
défaut voix historique est `minimax/speech-2.8-turbo` — c'est le genre d'écart que
le préflight tranche. On garde les valeurs historiques par défaut (zéro churn de
tests/fixtures) ; la surcharge env est le levier de correction immédiat.
"""

from __future__ import annotations

import os

IMAGE_MODEL: str = os.environ.get("VCM_IMAGE_MODEL", "bytedance/seedream-4.5")
VIDEO_MODEL: str = os.environ.get("VCM_VIDEO_MODEL", "prunaai/p-video")
VOICE_MODEL: str = os.environ.get("VCM_VOICE_MODEL", "minimax/speech-2.8-turbo")

# L'ordre est stable : image, vidéo, voix (utilisé par le préflight du harnais).
ALL_MODELS: tuple[str, ...] = (IMAGE_MODEL, VIDEO_MODEL, VOICE_MODEL)
