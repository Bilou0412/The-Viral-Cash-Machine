"""Rendu TEXTE complet d'un document vidéo — le descripteur EN ENTIER, lisible.

Le matériel texte EST le produit : ce qui décrit la vidéo et servira à la créer. Ici on
sérialise un `EditorDocument` en un « dossier » lisible de bout en bout — méta + intention,
bibles (décor + perso), puis chaque SCÈNE (décor référencé + variation) et chaque PLAN
(cadre, caméra, persos résolus, prompts IMAGE/MOUVEMENT compilés, narration, continuité).

Pur, sans I/O. Alimente `dogfood_editor.py --text` et la route `/script`.
"""

from __future__ import annotations

from .compile_shot import compile_image_prompt, compile_motion_prompt, resolve_shot
from .document import (
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    LocationEntry,
    Lumiere,
    Scene,
)


def _kv(label: str, value: str) -> list[str]:
    """Une ligne `label: value` — omise si value vide."""
    v = value.strip()
    return [f"  {label:<11}: {v}"] if v else []


def _lumiere(lum: Lumiere) -> str:
    return ", ".join(p for p in (lum.sources, lum.direction, lum.qualite,
                                 lum.temperature, lum.contraste) if p.strip())


def _location_block(loc: LocationEntry) -> str:
    lines = [f"  [{loc.ref}] {loc.lieu or '—'}"
             + (f" · {loc.echelle}" if loc.echelle else "")
             + (f" · {loc.int_ext}" if loc.int_ext else "")]
    lines += _kv("layout", loc.layout_spatial)
    lines += _kv("palette", loc.palette)
    lines += _kv("matières", loc.matieres)
    if loc.props_fixes:
        lines += _kv("props", ", ".join(loc.props_fixes))
    lines += _kv("lumière", _lumiere(loc.lumiere_base))
    return "\n".join(lines)


def _character_block(c: CharacterEntry) -> str:
    lines = [f"  [{c.id}] {c.name or '—'}" + (f" — {c.appearance}" if c.appearance else "")]
    lines += _kv("tenue", c.wardrobe)
    lines += _kv("voix", c.voice_id)
    lines += _kv("traits", c.traits)
    return "\n".join(lines)


def _plan_block(doc: EditorDocument, scene: Scene, brick: ClipBrick) -> str:
    """Un plan résolu (héritage + prompts compilés) rendu en texte."""
    assert brick.shot is not None
    r = resolve_shot(doc, scene, brick.shot)
    b = brick.shot
    dur = brick.placement.duration
    head = f"  ▸ PLAN {brick.id}  [{brick.kind}, {dur:g}s]"
    lines = [head]
    lines += _kv("intention", b.intention_plan)   # le POURQUOI du plan (le beat)
    lines += _kv("sujet", b.sujet)                 # sujet libre EN (plan sans perso)
    lines += _kv("cadre", ", ".join(p for p in (b.cadre.taille_plan, b.cadre.angle_hauteur,
                                                 b.cadre.focale) if p.strip()))
    lines += _kv("caméra", ", ".join(p for p in (b.camera.type, b.camera.vitesse,
                                                  b.camera.depart_arrivee) if p.strip()))
    for pp in b.personnages_presents:
        entry = r.bible.get(pp.ref)
        name = entry.name if entry else (pp.ref or "?")
        delta = f"{pp.etat_debut}→{pp.etat_fin}" if (pp.etat_debut or pp.etat_fin) else ""
        desc = ", ".join(p for p in (pp.action, delta, pp.expression) if p.strip())
        lines += _kv("perso", f"{name}" + (f" — {desc}" if desc else ""))
    lines += _kv("lumière", _lumiere(r.lumiere))
    narr = next((c.params.get("text", "") for c in brick.children
                 if c.role == "narration"), "")
    img = compile_image_prompt(r)
    mot = compile_motion_prompt(r)
    lines += _kv("IMAGE ▸", img)
    lines += _kv("MOUVEMT", mot)
    lines += _kv("VOIX", str(narr))
    links = " · ".join(p for p in (
        f"← {b.continuite.lien_precedent}" if b.continuite.lien_precedent else "",
        f"→ {b.continuite.lien_suivant}" if b.continuite.lien_suivant else "") if p)
    lines += _kv("continuité", links)
    return "\n".join(lines)


def _scene_block(doc: EditorDocument, scene: Scene,
                 bricks: dict[str, ClipBrick]) -> str:
    loc = next((locn for locn in doc.location_bible if locn.ref == scene.location_ref), None)
    lines = ["─" * 64, f"SCÈNE {scene.id} — {scene.title or ''}".rstrip(), "─" * 64]
    lines += _kv("décor", f"{loc.lieu} ({scene.location_ref})" if loc else scene.location_ref)
    lines += _kv("variation", ", ".join(p for p in (scene.saison, scene.moment_jour,
                                                     scene.meteo) if p.strip()))
    lines += _kv("mood", scene.mood)
    lines += _kv("lumière", _lumiere(scene.lumiere_ambiante))
    lines += _kv("ambiance", scene.ambiance_sonore)
    lines += _kv("intention", scene.intention_scene)
    lines.append("")
    # photo d'établissement (blob shot=None) puis plans
    if scene.environment_photo_ref in bricks:
        env = bricks[scene.environment_photo_ref]
        prompt = str(env.image.params.get("prompt", ""))
        lines.append(f"  ◈ ÉTABLISSEMENT {env.id}  [photo]")
        lines += _kv("IMAGE ▸", prompt)
        lines.append("")
    for sid in scene.shot_ids:
        brick = bricks.get(sid)
        if brick is not None and brick.shot is not None:
            lines.append(_plan_block(doc, scene, brick))
            lines.append("")
    return "\n".join(lines).rstrip()


def describe_document(doc: EditorDocument) -> str:
    """Le descripteur COMPLET de la vidéo, en texte lisible de bout en bout."""
    clips = {b.id: b for b in doc.bricks if isinstance(b, ClipBrick)}
    n_plans = sum(1 for b in clips.values() if b.shot is not None)
    total_s = sum(b.placement.duration for b in clips.values())
    m = doc.meta
    ig = doc.intention_globale

    out: list[str] = ["═" * 64, f"VIDÉO — {doc.title}", "═" * 64]
    fmt = f"{m.ratio}" + (f" {m.resolution}" if m.resolution else "") + f" {m.fps}fps"
    if m.style_rendu.strip():
        fmt += f" · style: {m.style_rendu}"
    out += _kv("format", fmt)
    out += _kv("intention", ", ".join(p for p in (ig.genre, ig.ton) if p.strip()))
    out += _kv("arc", ig.arc_narratif)
    out += _kv("musique", doc.musique_score)
    out += _kv("bilan", f"{total_s:g}s · {len(doc.scenes)} scène(s) · {n_plans} plan(s)")

    if doc.location_bible:
        out += ["", "DÉCORS (bible)"]
        out += [_location_block(loc) for loc in doc.location_bible]
    if doc.bible:
        out += ["", "PERSONNAGES (bible)"]
        out += [_character_block(c) for c in doc.bible]

    out.append("")
    for scene in doc.scenes:
        out.append(_scene_block(doc, scene, clips))
        out.append("")
    return "\n".join(out).rstrip() + "\n"
