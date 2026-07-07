"""Slugs de modèles Replicate — **source unique de vérité**.

Les identifiants envoyés à Replicate (image / vidéo i2v / voix). Ils étaient
dupliqués dans `services/pricing.py`, `replicate_provider.py` et
`scene_plan_to_document.py` → dérive garantie. On les centralise ici.

Vérifiés OK sur Replicate via `scripts/dogfood_editor.py --check` (dogfood réel).
"""

from __future__ import annotations

IMAGE_MODEL: str = "bytedance/seedream-4.5"
VIDEO_MODEL: str = "prunaai/p-video"
VOICE_MODEL: str = "minimax/speech-2.8-turbo"

# L'ordre est stable : image, vidéo, voix (utilisé par le préflight du harnais).
ALL_MODELS: tuple[str, ...] = (IMAGE_MODEL, VIDEO_MODEL, VOICE_MODEL)
