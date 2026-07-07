"""Compilateur du descripteur 3 niveaux → prompts modèle (v5).

Le matériel est réparti sur **Vidéo → Scène → Plan** (cf. `document.py`). Au build,
on **fusionne** (précédence **PLAN > SCÈNE > VIDÉO**) : la scène référence un décor
(`location_ref` → `LocationEntry`) et le fait varier ; le plan hérite de son décor,
sa lumière ambiante, son room tone — sauf s'il surcharge.

Chaque bloc part vers le bon modèle :
- `compile_image_prompt` → **prompt IMAGE** (la frame figée = état initial i2v) ;
- `compile_motion_prompt` → **prompt VIDÉO** (ce que le modèle interpole début→fin) ;
- `son.dialogue_voix` → texte de narration.

Les prompts compilés sont écrits dans `image.params["prompt"]` / `motion.params["prompt"]`
(cache lu par la génération/le spec/les labels — le rail bas ne change pas). Module pur.
"""

from __future__ import annotations

from dataclasses import dataclass

from .document import (
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    LocationEntry,
    Lumiere,
    PersonnagePresent,
    RenderMeta,
    Scene,
    ShotBrief,
)


def _join(parts: list[str], sep: str = ", ") -> str:
    return sep.join(p for p in (p.strip() for p in parts) if p)


def _lumiere_nonempty(lum: Lumiere) -> bool:
    return any((lum.sources, lum.direction, lum.qualite, lum.temperature, lum.contraste))


def _lumiere_phrase(lum: Lumiere) -> str:
    return _join([lum.sources, lum.direction, lum.qualite, lum.temperature, lum.contraste])


@dataclass
class ResolvedShot:
    """Un plan une fois l'héritage résolu (décor + lumière + contexte scène)."""

    brief: ShotBrief
    scene: Scene
    location: LocationEntry
    lumiere: Lumiere                     # override plan > ambiante scène > base décor
    meta: RenderMeta
    bible: dict[str, CharacterEntry]


def resolve_shot(doc: EditorDocument, scene: Scene, brief: ShotBrief) -> ResolvedShot:
    """Fusionne VIDÉO + SCÈNE + PLAN pour un plan donné (PLAN gagne les conflits)."""
    location = {locn.ref: locn for locn in doc.location_bible}.get(
        scene.location_ref, LocationEntry(ref="_none")
    )
    if brief.lumiere_override is not None:
        lumiere = brief.lumiere_override
    elif _lumiere_nonempty(scene.lumiere_ambiante):
        lumiere = scene.lumiere_ambiante
    else:
        lumiere = location.lumiere_base
    bible = {c.id: c for c in doc.bible if c.id}
    return ResolvedShot(brief, scene, location, lumiere, doc.meta, bible)


def _character_still(pp: PersonnagePresent, bible: dict[str, CharacterEntry]) -> str:
    """Le perso pour la FRAME de départ : apparence (bible) + tenue + état initial."""
    entry = bible.get(pp.ref)
    name = entry.name if entry else ""
    appearance = entry.appearance if entry else ""
    wardrobe = entry.wardrobe if entry else ""
    head = _join([name, f"({appearance})" if appearance else ""], sep=" ")
    return _join([head, f"wearing {wardrobe}" if wardrobe else "", pp.expression, pp.etat_debut])


def _character_motion(pp: PersonnagePresent, bible: dict[str, CharacterEntry]) -> str:
    """Le perso pour le MOUVEMENT : action + trajectoire + interpolation début→fin."""
    entry = bible.get(pp.ref)
    name = entry.name if entry else ""
    delta = _join([pp.etat_debut, f"to {pp.etat_fin}" if pp.etat_fin else ""], sep=" ")
    return _join([name, pp.action, pp.trajectoire, pp.vitesse, delta])


def compile_image_prompt(r: ResolvedShot) -> str:
    """La FRAME FIGÉE (état initial i2v) : décor résolu + cadre + persos au départ + style."""
    b, loc, sc = r.brief, r.location, r.scene
    people = _join([_character_still(pp, r.bible) for pp in b.personnages_presents], sep="; ")
    subject = _join([b.cadre.taille_plan, b.cadre.angle_hauteur, b.cadre.focale,
                     f"of {people}" if people else ""], sep=" ")
    place = _join([loc.lieu, loc.int_ext, sc.moment_jour, sc.saison, sc.meteo, loc.layout_spatial])
    setting = f"in {place}" if (subject and place) else place
    depth = _join([f"foreground {b.profondeur.avant_plan}" if b.profondeur.avant_plan else "",
                   f"midground {b.profondeur.plan_moyen}" if b.profondeur.plan_moyen else "",
                   f"background {b.profondeur.arriere_plan}" if b.profondeur.arriere_plan else ""])
    ambiance = _join([_lumiere_phrase(r.lumiere), loc.palette, loc.matieres, sc.mood])
    props = _join(loc.props_fixes)
    style = _join([r.meta.style_rendu, r.meta.grain_etalonnage, r.meta.epoque_defaut])
    return _join([subject, setting, depth, props, ambiance, style])


def compile_motion_prompt(r: ResolvedShot) -> str:
    """LE MOUVEMENT (interpolé par l'i2v) : caméra + actions début→fin + physique."""
    b = r.brief
    camera = _join([f"camera {b.camera.type}" if b.camera.type else "", b.camera.vitesse,
                    b.camera.depart_arrivee, b.cadre.mise_au_point])
    people = _join([_character_motion(pp, r.bible) for pp in b.personnages_presents], sep="; ")
    secondary = _join([_join([e.quoi, e.mouvement,
                              _join([e.etat_debut, f"to {e.etat_fin}" if e.etat_fin else ""], sep=" ")])
                       for e in b.elements_secondaires], sep="; ")
    physics = _join([_join([p.element, p.comportement, p.intensite_direction])
                     for p in b.physique_environnement], sep="; ")
    light_time = _join([b.lumiere_temps.ce_qui_change, b.lumiere_temps.depart_arrivee])
    return _join([camera, people, secondary, physics, light_time])


def recompile_document(doc: EditorDocument) -> None:
    """Réécrit `image.params['prompt']` ET `motion.params['prompt']` des briques
    portant un `shot`, en résolvant l'héritage scène→plan. Briques sans `shot`
    (blob legacy) laissées telles quelles."""
    scene_of: dict[str, Scene] = {}
    for scene in doc.scenes:
        for sid in (*scene.shot_ids, scene.environment_photo_ref):
            if sid:
                scene_of[sid] = scene
    for brick in doc.bricks:
        if isinstance(brick, ClipBrick) and brick.shot is not None:
            r = resolve_shot(doc, scene_of.get(brick.id, Scene(id="_none")), brick.shot)
            # Champs structurés = source de vérité QUAND non vides ; sinon on garde
            # le cache (ne jamais effacer un prompt existant avec du vide).
            if img := compile_image_prompt(r):
                brick.image.params["prompt"] = img
            if brick.motion is not None and (mot := compile_motion_prompt(r)):
                brick.motion.params["prompt"] = mot
