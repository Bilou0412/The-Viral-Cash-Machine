"""Compilateur du plan structuré → prompt visuel (v4).

Une vraie boîte de prod décrit un plan par départements (déco, lumière, cadrage,
personnages) ; au tournage, tout est REGROUPÉ. Ici : `ShotBrief` (champs métier)
+ la `bible` des personnages → LE prompt EN envoyé au modèle image/vidéo.

`ShotBrief` est la source de vérité ; le prompt compilé est écrit dans
`image.params["prompt"]` (cache d'affichage + ce que lit la génération). Une
brique sans `shot` garde son prompt-blob legacy (rétro-compat).

Module pur (aucune I/O), import-light — miroir léger de `context.compile_prompt`.
"""

from __future__ import annotations

from .document import (
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    ShotBrief,
    ShotCharacter,
)


def _join(parts: list[str], sep: str = ", ") -> str:
    return sep.join(p for p in (p.strip() for p in parts) if p)


def _character_phrase(sc: ShotCharacter, bible: dict[str, CharacterEntry]) -> str:
    """Un personnage présent → un fragment EN (identité bible + surcharges du plan)."""
    entry = bible.get(sc.ref)
    name = (entry.name if entry else "") or sc.name
    appearance = entry.appearance if entry else ""
    wardrobe = sc.wardrobe or (entry.wardrobe if entry else "")
    # « Léa (red-haired teen) wearing a torn raincoat, terrified, running »
    head = _join([name, f"({appearance})" if appearance else ""], sep=" ")
    tail = _join(
        [
            f"wearing {wardrobe}" if wardrobe else "",
            sc.expression,
            sc.action,
        ]
    )
    return _join([head, tail])


def compile_shot_prompt(shot: ShotBrief, bible: list[CharacterEntry]) -> str:
    """Regroupe les champs métier d'un plan en LE prompt EN (déterministe).

    Ordre : cadrage → personnages → décor → lumière → extra. Les parties vides
    sont ignorées ; les refs bible sont résolues et surchargées. L'art direction
    GLOBALE n'est PAS incluse ici : elle est ajoutée à la génération par
    `context.compile_prompt` (éviter la double injection).
    """
    by_id = {c.id: c for c in bible if c.id}
    people = _join([_character_phrase(sc, by_id) for sc in shot.characters], sep="; ")

    subject = _join([shot.cadrage, f"of {people}" if people else ""], sep=" ")
    # Avec un sujet, le décor est un complément (« in {decor} ») ; sans sujet (photo
    # d'environnement), le décor mène la description.
    decor = shot.decor.strip()
    decor_part = (f"in {decor}" if subject else decor) if decor else ""
    return _join([subject, decor_part, shot.lumiere, shot.extra])


def recompile_document(doc: EditorDocument) -> None:
    """Réécrit `image.params['prompt']` de chaque brique PORTANT un `shot`.

    Sync le cache lisible par la génération/le spec/les labels avec les champs
    métier. Les briques sans `shot` (blob legacy) sont laissées telles quelles.
    """
    for brick in doc.bricks:
        if isinstance(brick, ClipBrick) and brick.shot is not None:
            brick.image.params["prompt"] = compile_shot_prompt(brick.shot, doc.bible)
