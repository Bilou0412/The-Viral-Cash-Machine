"""Slugs de modèles Replicate — **source unique de vérité**.

Les identifiants envoyés à Replicate (image / vidéo i2v / voix). Ils étaient
dupliqués dans `services/pricing.py`, `replicate_provider.py` et
`scene_plan_to_document.py` → dérive garantie. On les centralise ici.

Vérifiés OK sur Replicate via `scripts/dogfood_editor.py --check` (dogfood réel).
"""

from __future__ import annotations

from dataclasses import dataclass

IMAGE_MODEL: str = "bytedance/seedream-4.5"
VIDEO_MODEL: str = "prunaai/p-video"
VOICE_MODEL: str = "minimax/speech-2.8-turbo"

# L'ordre est stable : image, vidéo, voix (utilisé par le préflight du harnais).
ALL_MODELS: tuple[str, ...] = (IMAGE_MODEL, VIDEO_MODEL, VOICE_MODEL)


# -- Capacités des modèles vidéo i2v ------------------------------------------
# L'HORIZON DE COHÉRENCE d'un modèle i2v = la durée max qu'il tient sans dériver
# (visages/mains qui morphent, décor qui glisse). C'est une **capacité du modèle**,
# PAS une constante produit : au-delà, on n'allonge pas un plan — on enchaîne des
# scènes. Distinct du plafond de PARAMÈTRE de l'API (`prunaai/p-video` accepte
# jusqu'à 20 s, mais 20 s n'est qu'une borne de champ, pas une garantie de cohérence).


@dataclass(frozen=True)
class VideoModelCaps:
    """Les capacités d'un modèle vidéo qui contraignent le découpage."""

    max_coherent_duration_s: float


# Indexé par slug **owner/name** (jamais la version). `prunaai/p-video` = Wan 2.2
# distillé (Pruna « juiced ») : défaut natif 5 s, optimisé/benchmarké à cette durée.
VIDEO_MODEL_CAPS: dict[str, VideoModelCaps] = {
    VIDEO_MODEL: VideoModelCaps(max_coherent_duration_s=5.0),
}
# Défaut prudent pour un slug inconnu (bord bas de l'état de l'art i2v distillé).
_DEFAULT_MAX_COHERENT_S: float = 5.0


def effective_video_slug(model_ref: str) -> str:
    """Le slug vidéo effectif d'un `model_ref` (repli = modèle par défaut).

    UN SEUL point de résolution, partagé par le préflight / le clamp / le coût :
    l'abstraction par-slug ne doit jamais être résolue de trois façons différentes
    (sinon on valide contre un horizon et on rend avec un autre). Normalise en
    `owner/name` (la table de capacités ignore la version).
    """
    slug = model_ref.strip() or VIDEO_MODEL
    return slug.split(":", 1)[0]


def max_coherent_duration_s(slug: str) -> float:
    """L'horizon de cohérence (secondes) du modèle vidéo `slug` (défaut si inconnu)."""
    caps = VIDEO_MODEL_CAPS.get(effective_video_slug(slug))
    return caps.max_coherent_duration_s if caps else _DEFAULT_MAX_COHERENT_S
