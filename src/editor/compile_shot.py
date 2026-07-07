"""Compilateur du descripteur 3 niveaux → prompts modèle (v5).

Le matériel est réparti sur **Vidéo → Scène → Plan** (cf. `document.py`). Au build,
on **fusionne** (précédence **PLAN > SCÈNE > VIDÉO**) : la scène référence un décor
(`location_ref` → `LocationEntry`) et le fait varier ; le plan hérite de son décor,
sa lumière ambiante, son room tone — sauf s'il surcharge.

Chaque bloc part vers le bon modèle :
- `compile_image_prompt` → **prompt IMAGE** (la frame figée = état initial i2v) ;
- `compile_motion_prompt` → **prompt VIDÉO** (ce que le modèle interpole début→fin) ;
- `son.dialogue_voix` → texte de narration.

**Discipline (T-DESC-3).** Les modèles image/vidéo rendent mieux des prompts COURTS,
en ANGLAIS, sujet-en-tête, sans redondance. On applique donc, de façon déterministe :
budget de mots dur (`_MAX_IMAGE_WORDS`/`_MAX_MOTION_WORDS`, troncature par blocs
entiers), **dédup structurelle** (un seul système spatial = la profondeur ; lumière
courte ; on laisse tomber `layout_spatial`/`matieres`/`props_fixes` bruts), le
**mouvement = le delta seul** (états qui changent, 1 caméra, ≤1 ambient), et une
**normalisation FR→EN** des champs à vocabulaire fermé (int/ext, moment, saison, météo).

Les prompts compilés sont écrits dans `image.params["prompt"]` / `motion.params["prompt"]`
(cache lu par la génération/le spec/les labels — le rail bas ne change pas). Module pur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .document import (
    Cadre,
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

# Budgets de mots (filet de sécurité ; l'assemblage tronque par blocs entiers).
_MAX_IMAGE_WORDS = 60
_MAX_MOTION_WORDS = 35
# Cap PAR personnage — borne les scènes d'ensemble (sinon 3 persos = 90+ mots).
_MAX_CHAR_STILL_WORDS = 16
_MAX_CHAR_MOTION_WORDS = 18

# Jetons « vides » que le LLM émet parfois — on les traite comme absents.
_JUNK = {"", "-", "--", "n/a", "na", "none", "null", "nil", "unknown", "aucun", "aucune"}
# Deltas nuls (état final == pas de changement) → aucun mouvement à décrire.
_UNCHANGED = {"unchanged", "same", "idem", "static", "still", "none", "n/a"}
# Types caméra considérés comme immobiles (→ « static camera », on ignore vitesse/trajet).
_STATIC_CAM = {"static", "fixe", "fixed", "locked", "still", "none", "immobile"}
# Garde-robe placeholder (chat « natural fur only », perso nu…) → pas de « wearing … ».
_WARDROBE_SKIP = re.compile(r"^(no clothing|nude|naked|natural fur.*|none|n/?a)$", re.I)

# Normalisation FR→EN des champs à VOCABULAIRE FERMÉ (les modèles attendent l'anglais).
# Appliqué par remplacement de sous-chaîne, phrases longues d'abord (cf. `_EN_PHRASES`).
_EN_MAP: dict[str, str] = {
    # int / ext
    "intérieur": "interior", "interieur": "interior", "int": "interior",
    "extérieur": "exterior", "exterieur": "exterior", "ext": "exterior",
    # moment du jour
    "petit matin": "dawn", "aube": "dawn", "lever du soleil": "sunrise",
    "matin": "morning", "matinée": "morning", "matinee": "morning",
    "midi": "noon", "fin d'après-midi": "late afternoon",
    "fin d'apres-midi": "late afternoon", "après-midi": "afternoon",
    "apres-midi": "afternoon", "coucher du soleil": "sunset",
    "crépuscule": "dusk", "crepuscule": "dusk", "soirée": "evening",
    "soiree": "evening", "soir": "evening", "nuit": "night",
    # saisons
    "printemps": "spring", "été": "summer", "ete": "summer",
    "automne": "autumn", "hiver": "winter",
    # météo
    "temps clair": "clear sky", "ciel clair": "clear sky", "ensoleillé": "sunny",
    "ensoleille": "sunny", "nuageux": "cloudy", "couvert": "overcast",
    "pluie légère": "light rain", "pluie legere": "light rain", "pluie": "rain",
    "orage": "storm", "neige": "snow", "brouillard": "fog", "brume": "mist",
    "vent": "wind", "venteux": "windy", "sec": "dry", "humide": "damp",
}
_EN_PHRASES: list[tuple[str, str]] = sorted(
    _EN_MAP.items(), key=lambda kv: len(kv[0]), reverse=True
)
# Angles de caméra → tags anglais canoniques.
_ANGLE_MAP: list[tuple[str, str]] = [
    ("contre-plongée", "low-angle"), ("contre-plongee", "low-angle"),
    ("plongée", "high-angle"), ("plongee", "high-angle"),
    ("hauteur d'œil", "eye-level"), ("hauteur d'oeil", "eye-level"),
    ("niveau des yeux", "eye-level"), ("eye level", "eye-level"),
    ("low", "low-angle"), ("high", "high-angle"), ("eye", "eye-level"),
]

# Repérage de régression : des MOTS-OUTILS français dans un prompt censé être EN.
# (On ne teste PAS les accents seuls : les prénoms FR — « Léa » — en portent légitimement.)
_FRENCH_HINT = re.compile(
    r"\b(le|la|les|dans|avec|une|des|du|aux|pour|sur|sous|c'est|il y a)\b", re.I
)


def _clean(value: str) -> str:
    """Vide les placeholders (« N/A », « none »…) et rogne la ponctuation parasite
    (virgules en fin que le LLM laisse traîner) — évite de les injecter au prompt."""
    v = value.strip().strip(",;").strip()
    return "" if v.lower() in _JUNK else v


def _tidy(text: str) -> str:
    """Nettoyage final : virgules répétées (« a,, b »), espaces, bords."""
    text = re.sub(r"(\s*,\s*){2,}", ", ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,;")


def _join(parts: list[str], sep: str = ", ") -> str:
    return sep.join(p for p in (p.strip() for p in parts) if p)


def _cap_words(text: str, n: int) -> str:
    words = text.split()
    capped = " ".join(words[:n]) if len(words) > n else text
    return capped.rstrip(" ,;")   # jamais de virgule pendante après troncature


def _assemble(blocks: list[str], max_words: int) -> str:
    """Concatène des blocs par saillance décroissante SANS dépasser le budget mots.
    Tronque par bloc ENTIER (jamais au milieu) ; garde toujours au moins le 1er (sujet)."""
    out: list[str] = []
    used = 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        n = len(block.split())
        if out and used + n > max_words:
            break
        out.append(block)
        used += n
    return ", ".join(out)


def _en(value: str) -> str:
    """Traduit un champ à vocabulaire fermé FR→EN (déterministe, best-effort).

    Remplacement par MOTS ENTIERS (`\\b…\\b`) — sinon « int » collerait dans
    « interior ». Match exact d'abord (rapide et exhaustif pour un mono-mot)."""
    s = _clean(value)
    if not s:
        return ""
    low = s.lower()
    if low in _EN_MAP:
        return _EN_MAP[low]
    out = low
    for fr, en in _EN_PHRASES:
        out = re.sub(rf"\b{re.escape(fr)}\b", en, out)
    return out if out != low else s


def _angle(value: str) -> str:
    s = _clean(value)
    if not s:
        return ""
    low = s.lower()
    for fr, en in _ANGLE_MAP:
        if fr in low:
            return en
    return s


def _delta(a: str, b: str) -> str:
    """Le signal d'interpolation début→fin. "" si pas de vrai changement (a==b, b vide/nul)."""
    a, b = _clean(a), _clean(b)
    if not b or b.lower() in _UNCHANGED or a.lower() == b.lower():
        return ""
    return f"{a} to {b}" if a else b


def _first_nonempty(items: list[str]) -> str:
    for it in items:
        if it.strip():
            return it
    return ""


def _dedup_tokens(text: str) -> str:
    """Déduplique les mots (insensible casse) en préservant l'ordre — pour les tags de style."""
    seen: set[str] = set()
    out: list[str] = []
    for tok in text.replace(",", " ").split():
        k = tok.lower()
        if k and k not in seen:
            seen.add(k)
            out.append(tok)
    return " ".join(out)


def _lumiere_nonempty(lum: Lumiere) -> bool:
    return any((lum.sources, lum.direction, lum.qualite, lum.temperature, lum.contraste))


def _lumiere_short(lum: Lumiere) -> str:
    """Une lumière en 1 syntagme court (≤6 mots) : les 2 champs les plus saillants."""
    parts = [_clean(lum.sources), _clean(lum.qualite),
             _clean(lum.temperature), _clean(lum.direction)]
    return _cap_words(_join([p for p in parts if p][:2]), 6)


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


def _is_tight_frame(cadre: Cadre) -> bool:
    """Cadre serré (gros plan) → le bas du corps est hors champ : on omet la garde-robe."""
    t = cadre.taille_plan.lower()
    return "close" in t or "gros plan" in t or "macro" in t or "insert" in t


def _character_still(pp: PersonnagePresent, bible: dict[str, CharacterEntry],
                     tight_frame: bool) -> str:
    """Le perso pour la FRAME de départ : nom + apparence courte + tenue + expression.

    Pas d'`etat_debut` (c'est le delta → motion). Apparence capée (ancre d'identité
    nécessaire à chaque plan, mais courte). Garde-robe omise si placeholder ou cadre serré.
    """
    entry = bible.get(pp.ref)
    name = entry.name if entry else ""
    appearance = _cap_words(_clean(entry.appearance) if entry else "", 12)
    wardrobe = "" if (tight_frame or entry is None) else _clean(entry.wardrobe)
    if wardrobe and _WARDROBE_SKIP.match(wardrobe):
        wardrobe = ""
    head = _join([name, f"({appearance})" if appearance else ""], sep=" ")
    still = _join([head, f"wearing {wardrobe}" if wardrobe else "", _clean(pp.expression)])
    return _cap_words(still, _MAX_CHAR_STILL_WORDS)


def _character_motion(pp: PersonnagePresent, bible: dict[str, CharacterEntry]) -> str:
    """Le perso pour le MOUVEMENT : action + trajectoire + interpolation début→fin."""
    entry = bible.get(pp.ref)
    name = entry.name if entry else ""
    motion = _join([name, _clean(pp.action), _clean(pp.trajectoire), _clean(pp.vitesse),
                    _delta(pp.etat_debut, pp.etat_fin)])
    return _cap_words(motion, _MAX_CHAR_MOTION_WORDS)


def _framing(cadre: Cadre) -> str:
    """Le cadrage en tag court et grammatical : taille, angle (EN), focale."""
    return _join([_clean(cadre.taille_plan), _angle(cadre.angle_hauteur), _clean(cadre.focale)])


def compile_image_prompt(r: ResolvedShot) -> str:
    """La FRAME FIGÉE (état initial i2v), EN, sujet-en-tête, dédupliquée, ≤60 mots.

    Ordre de saillance : SUJET (persos + cadrage) → SETTING (lieu + moment) →
    COMPOSITION (profondeur) → AMBIANCE (lumière courte + palette) → STYLE.
    """
    b, loc, sc = r.brief, r.location, r.scene
    tight = _is_tight_frame(b.cadre)

    # Un bloc PAR personnage (l'assembleur tronque proprement les scènes d'ensemble).
    people = [s for pp in b.personnages_presents
              if (s := _character_still(pp, r.bible, tight))]
    framing = _framing(b.cadre)

    place = _join([_clean(loc.lieu), _en(loc.int_ext), _en(sc.moment_jour),
                   _en(sc.saison), _en(sc.meteo)])
    setting = _cap_words(f"in {place}" if place else "", 14)

    # Chaque plan de profondeur capé SÉPARÉMENT (jamais un label « background » orphelin).
    depth = _join([
        f"foreground {_cap_words(_clean(b.profondeur.avant_plan), 6)}"
        if _clean(b.profondeur.avant_plan) else "",
        f"midground {_cap_words(_clean(b.profondeur.plan_moyen), 6)}"
        if _clean(b.profondeur.plan_moyen) else "",
        f"background {_cap_words(_clean(b.profondeur.arriere_plan), 6)}"
        if _clean(b.profondeur.arriere_plan) else "",
    ])

    ambiance = _cap_words(_join([_lumiere_short(r.lumiere), _clean(loc.palette)]), 8)

    # Le mood suit le beat DU PLAN : porté par l'expression du perso (déjà dans `subject`) ;
    # `sc.mood` seulement en fallback (sinon il se répète, identique, sur tous les plans).
    has_expr = any(_clean(pp.expression) for pp in b.personnages_presents)
    mood = "" if has_expr else _clean(sc.mood)
    style = _cap_words(_dedup_tokens(_join(
        [_clean(r.meta.style_rendu), _clean(r.meta.grain_etalonnage),
         _clean(r.meta.epoque_defaut), mood])), 10)

    return _tidy(_assemble([*people, framing, setting, depth, ambiance, style],
                           _MAX_IMAGE_WORDS))


def compile_motion_prompt(r: ResolvedShot) -> str:
    """LE MOUVEMENT (interpolé par l'i2v) = LE DELTA SEUL, ≤35 mots.

    Persos d'abord (signal principal) : action + delta début→fin. Puis la caméra
    (1 syntagme, « static camera » si immobile). Puis AU PLUS 1 élément secondaire et
    1 phénomène physique. Les deltas nuls (`X to X`, « none »…) sont éliminés.
    """
    b = r.brief
    cam_type = _clean(b.camera.type)
    if not cam_type or cam_type.lower() in _STATIC_CAM:
        camera = "static camera"
    else:
        camera = _join([f"camera {cam_type}", _clean(b.camera.vitesse),
                        _clean(b.camera.depart_arrivee)])

    # Un bloc PAR personnage — le signal principal ; l'assembleur borne l'ensemble.
    people = [m for pp in b.personnages_presents
              if (m := _character_motion(pp, r.bible))]

    secondary = _first_nonempty([
        _join([_clean(e.quoi), _clean(e.mouvement), _delta(e.etat_debut, e.etat_fin)])
        for e in b.elements_secondaires
    ])
    physics = _first_nonempty([
        _join([_clean(p.element), _clean(p.comportement), _clean(p.intensite_direction)])
        for p in b.physique_environnement
    ])
    light_time = _join([_clean(b.lumiere_temps.ce_qui_change),
                        _clean(b.lumiere_temps.depart_arrivee)])

    # Caméra en tête (courte, toujours pertinente) → garantie même en scène d'ensemble.
    return _tidy(_assemble([camera, *people, secondary, physics, light_time],
                           _MAX_MOTION_WORDS))


def looks_french(prompt: str) -> bool:
    """Heuristique de régression : le prompt visuel (censé EN) contient-il du FR ?"""
    return bool(_FRENCH_HINT.search(prompt))


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
