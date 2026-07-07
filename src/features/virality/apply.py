"""Appliquer une variante de hook GAGNANTE au document — pur, sans I/O.

Le classement ne sert à rien s'il ne change pas la vidéo. Ici on injecte l'ouverture
gagnante dans la PREMIÈRE brique du document (la frame d'établissement) : son prompt
image devient le `first_shot_prompt` du hook, et sa narration d'ouverture (si présente)
devient l'accroche `hook_text`.

La 1re brique est un blob `shot=None` (photo d'établissement / intro) → `recompile_document`
ne l'écrase pas : le hook TIENT après resync. On ne touche donc jamais aux briques `shot`
(leur prompt reste dérivé des champs métier)."""

from __future__ import annotations

from ...editor.document import ClipBrick, EditorDocument
from .model import HookVariant


def apply_hook_to_document(doc: EditorDocument, variant: HookVariant) -> bool:
    """Injecte l'ouverture gagnante dans la 1re brique. Renvoie True si appliqué.

    No-op (False) si le document n'a aucune brique clip ou si la variante est vide.
    """
    opening = next((b for b in doc.bricks if isinstance(b, ClipBrick)), None)
    if opening is None:
        return False
    applied = False
    if variant.first_shot_prompt.strip():
        opening.image.params["prompt"] = variant.first_shot_prompt.strip()
        applied = True
    if variant.hook_text.strip():
        for child in opening.children:
            if child.role == "narration":
                child.params["text"] = variant.hook_text.strip()
                applied = True
                break
    return applied
