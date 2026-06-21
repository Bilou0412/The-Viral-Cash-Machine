"""Pont ClipBrick ↔ contrats de capacité (B2).

Les contrats de capacité (`features.compositing.registry`) sont indexés par
**kind de nœud** — `image` / `video` / `voice` — et `validate_params` vérifie
qu'un dict de params plat porte les champs requis d'un kind. Mais une `ClipBrick`
est COMPOSITE : son nœud `image` est un frère du `motion`, et la durée d'une vidéo
peut venir du `placement`. Une validation naïve `validate_params("video",
motion.params)` signalerait donc à tort `image`/`duration` manquants.

Ce module encode la validation **composite-aware**, alignée exactement sur ce que
`document_to_spec` (B1) suppose :

- nœud `image`        → contrat `image` (prompt requis) ;
- nœud `motion` (vidéo) → contrat `video`, mais `image` est fourni par le nœud
  frère et `duration` peut venir du `placement` → on ne les réclame pas dans
  `motion.params` ; le `prompt` peut retomber sur celui de l'image ;
- enfant audio        → `text` requis ; `voice_id` requis seulement pour une
  narration (TTS), optionnel pour un dialogue (voix native du modèle vidéo).

Sert de pré-vol à B4 (génération idempotente) et à B3 (signaler les briques
incomplètes). Import-light (registry est sans dépendance lourde).

Ce module n'est PAS importé par `editor/__init__` (pour garder l'import du package
limité à pydantic+videospec) : `from src.editor.capabilities import validate_clip`.
"""

from __future__ import annotations

from typing import Dict, List

from ..features.compositing.registry import get_contract, validate_params
from .document import ClipBrick, GenNode

# Quel contrat de capacité s'applique à chaque type de nœud d'un clip.
_NODE_KIND = {"image": "image", "motion": "video", "audio": "voice"}


def _has(params: Dict[str, object], contract_kind: str, field_name: str) -> bool:
    """True si ``field_name`` (ou un de ses alias du contrat) est présent et non None."""
    present = {k for k, v in params.items() if v is not None}
    for fld in get_contract(contract_kind).fields:
        if fld.name == field_name:
            return bool(present.intersection((fld.name, *fld.aliases)))
    return field_name in present


def validate_clip(clip: ClipBrick) -> Dict[str, List[str]]:
    """Champs REQUIS manquants par nœud du clip. Dict vide = clip prêt à générer.

    Clés : ``"image"``, ``"motion"`` (clips vidéo), ``"child:<id>"`` (enfants
    audio). Valeurs : la liste des champs canoniques manquants pour ce nœud.
    """
    issues: Dict[str, List[str]] = {}

    img_missing = validate_params("image", clip.image.params)
    if img_missing:
        issues["image"] = img_missing
    has_image_prompt = _has(clip.image.params, "image", "prompt")

    if clip.kind == "video":
        motion = clip.motion or GenNode()
        eff = dict(motion.params)
        eff["image"] = "<frame frère>"  # fourni par le nœud image, pas par le motion
        if not _has(eff, "video", "prompt") and has_image_prompt:
            eff["prompt"] = "<repli image>"
        if not _has(eff, "video", "duration") and clip.placement.duration > 0:
            eff["duration"] = clip.placement.duration
        motion_missing = validate_params("video", eff)
        if motion_missing:
            issues["motion"] = motion_missing

    for child in clip.children:
        missing: List[str] = []
        if not _has(child.params, "voice", "text"):
            missing.append("text")
        if child.role == "narration" and not _has(child.params, "voice", "voice_id"):
            missing.append("voice_id")
        if missing:
            issues[f"child:{child.id}"] = missing

    return issues


def clip_is_ready(clip: ClipBrick) -> bool:
    """True si tous les nœuds requis du clip ont leurs champs (générable)."""
    return not validate_clip(clip)


def clip_node_kinds(clip: ClipBrick) -> Dict[str, str]:
    """Nœud → kind de contrat, pour que B3 sache quel formulaire/modèles montrer.

    ``form_descriptor`` (model_catalog) et ``get_contract(kind).preferred_models``
    se branchent ensuite sur ces kinds.
    """
    kinds = {"image": _NODE_KIND["image"]}
    if clip.kind == "video":
        kinds["motion"] = _NODE_KIND["motion"]
    for child in clip.children:
        kinds[f"child:{child.id}"] = _NODE_KIND["audio"]
    return kinds
