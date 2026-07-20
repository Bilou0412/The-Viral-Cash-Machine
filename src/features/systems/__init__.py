"""Feature SYSTEMS — format « Système expliqué » (image → explication en scènes).

Le moule #3 : on part d'une IMAGE d'un système (bâtiment, composant, foule, chantier…),
on l'analyse, et on produit un SCRIPT qui explique comment ça fonctionne / se construit,
découpé en plans COURTS (≤ horizon i2v = 5 s). Sortie = le même `VideoPlan` que les
scènes → passe par `scene_plan_to_document` + le rail commun (compile_shot, describe,
document_to_spec). Port `SystemExplainer` : Fake offline + OpenAI (vision) injectés au bord.
"""

from __future__ import annotations

from .ports import DEFAULT_STEPS, SystemExplainer, SystemExplainError

__all__ = ["DEFAULT_STEPS", "SystemExplainError", "SystemExplainer"]
