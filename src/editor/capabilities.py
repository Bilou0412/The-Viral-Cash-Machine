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

from ._fields import field_present, missing_required
from .document import ClipBrick, GenNode

# Quel contrat de capacité s'applique à chaque type de nœud d'un clip.
_NODE_KIND = {"image": "image", "motion": "video", "audio": "voice"}


def validate_clip(clip: ClipBrick) -> dict[str, list[str]]:
    """Champs REQUIS manquants par nœud du clip. Dict vide = clip prêt à générer.

    Clés : ``"image"``, ``"motion"`` (clips vidéo), ``"child:<id>"`` (enfants
    audio), ``"zoom"`` (PHOTO zoomée sans narration). Valeurs : la liste des
    champs canoniques manquants pour ce nœud.

    INVARIANT garanti : ``validate_clip(c) == {}`` ⟹ ``document_to_spec`` réussit
    sur ``c`` sans lever ni produire d'asset au prompt/texte vide. Le validateur
    et le compilateur partagent ``_fields`` (mêmes alias, même règle « vide »).
    """
    issues: dict[str, list[str]] = {}

    img_missing = missing_required(clip.image.params, "image")
    if img_missing:
        issues["image"] = img_missing
    has_image_prompt = field_present(clip.image.params, "image", "prompt")

    if clip.kind == "video":
        motion = clip.motion or GenNode()
        eff = dict(motion.params)
        eff["image"] = "<frame frère>"  # fourni par le nœud image, pas par le motion
        if not field_present(eff, "video", "prompt") and has_image_prompt:
            eff["prompt"] = "<repli image>"
        if not field_present(eff, "video", "duration") and clip.placement.duration > 0:
            eff["duration"] = clip.placement.duration
        motion_missing = missing_required(eff, "video")
        if motion_missing:
            issues["motion"] = motion_missing

    for child in clip.children:
        missing: list[str] = []
        if not field_present(child.params, "voice", "text"):
            missing.append("text")
        if child.role == "narration" and not field_present(child.params, "voice", "voice_id"):
            missing.append("voice_id")
        if missing:
            issues[f"child:{child.id}"] = missing

    # PHOTO zoomée sans aucun enfant audio : non rendable (NarrationSegment exige
    # un audio, IntroSegment n'a pas de zoom) → le compilateur lèverait. On le
    # signale ici pour garantir l'invariant « ready ⟹ compile réussit ».
    if clip.kind == "photo" and clip.zoom is not None and not clip.children:
        issues["zoom"] = ["narration"]

    return issues


def clip_is_ready(clip: ClipBrick) -> bool:
    """True si tous les nœuds requis du clip ont leurs champs (générable)."""
    return not validate_clip(clip)


def clip_node_kinds(clip: ClipBrick) -> dict[str, str]:
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
