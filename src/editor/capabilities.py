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

from ._fields import field_present, field_value, missing_required
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


def _effective_video_duration(clip: ClipBrick) -> float | None:
    """La durée effective d'un clip VIDÉO — MÊME précédence que `compile_spec._video_asset`
    (`compile_spec.py:85-87`) : `motion.params['duration']>0` → `placement.duration>0`,
    sinon None (manquante). On NE lit PAS le span de la timeline ici, exprès : le
    compilateur ne le lit pas → le validateur et le compilateur ne doivent jamais
    diverger sur ce qu'est « la durée » (sinon un plan valide pour l'un est corrompu
    pour l'autre)."""
    motion = clip.motion or GenNode()
    dur = field_value(motion.params, "video", "duration")
    if not isinstance(dur, bool) and isinstance(dur, (int, float)) and dur > 0:
        return float(dur)
    if clip.placement.duration > 0:
        return float(clip.placement.duration)
    return None


def _beat_count(clip: ClipBrick) -> int:
    """Nombre de beats d'ACTION distincts dans la timeline du plan.

    Un beat = un mouvement propre. Plusieurs `Segment` qui **phrasent le même geste**
    (accel→tenue→décel, même `action_sujet`) = 1 beat ; des `action_sujet` DIFFÉRENTS =
    une suite d'actions = plusieurs beats (le plan devrait être scindé).

    ATTENTION — heuristique de SURFACE (compte les `action_sujet` distincts après
    normalisation basse-casse) : « elle avance » vs « elle s'avance » comptent pour 2.
    Elle est calibrée pour de l'**ADVISORY** (un warning non bloquant, coût d'un faux
    positif ~nul), PAS pour du CONTRÔLE. Un futur lot d'auto-split NE DOIT PAS s'y
    appuyer sans la durcir d'abord (sinon un faux positif scinde un plan à tort)."""
    if clip.shot is None:
        return 0
    actions = {a.strip().lower() for seg in clip.shot.timeline if (a := seg.action_sujet.strip())}
    return len(actions)


def validate_shot_duration(clip: ClipBrick, *, max_coherent_s: float) -> dict[str, list[str]]:
    """Signale un plan à SCINDER (durée > horizon modèle, ou densité de beats > 1)
    ou CORROMPU (durée vidéo manquante). Frère de `validate_clip` : même convention
    ``dict[str, list[str]]`` (``{}`` = OK).

    NB : c'est un **signal de scission**, PAS un clamp — le dépassement d'horizon
    n'est jamais raboté en silence ici ; il est rendu visible pour piloter un split.
    Clip sans `shot` (blob legacy) → ``{}`` (rien à juger)."""
    if clip.shot is None:
        return {}
    issues: dict[str, list[str]] = {}
    if clip.kind == "video":
        dur = _effective_video_duration(clip)
        if dur is None:
            issues["motion"] = ["missing"]        # durée trouée = donnée corrompue
        elif dur > max_coherent_s:
            issues["motion"] = ["over_horizon"]   # trop long → scinder, pas raboter
    if _beat_count(clip) > 1:
        issues["beats"] = ["multi_beat"]          # suite d'actions → scinder
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
