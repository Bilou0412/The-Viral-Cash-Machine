"""Décrypteur de scènes OpenAI — deux phases, neutre (aucun CYOA).

Phase MACRO : idée → liste de scènes (titre + photo d'environnement + intention).
Phase MICRO : chaque scène → plans courts (visuel EN, mouvement EN, narration FR),
en portant un résumé courant pour la continuité de l'arc. Miroir structurel de
`openai_adventure_decomposer._decompose_chronology`, prompts génériques.

Convention langue : ``*_desc`` = anglais (prompt visuel) ; narration = français.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError

from ...editor.document import (
    Cadre,
    Camera,
    ElementSecondaire,
    IntentionGlobale,
    LocationEntry,
    Lumiere,
    LumiereTemps,
    Physique,
    Profondeur,
    RenderMeta,
    Son,
)
from .model import CharacterPlan, ScenePlan, ShotCharacterPlan, ShotPlan, VideoPlan
from .ports import DEFAULT_SCENES, SceneDecompositionError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_MAX_SHOTS = 4


def _to_str(v: object) -> object:
    """Le LLM renvoie parfois une liste là où on attend une chaîne (traits, matières…)."""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return v


# Chaîne tolérante : accepte aussi une liste (jointe) — robustesse au JSON du LLM.
LooseStr = Annotated[str, BeforeValidator(_to_str)]

# Libellés pilotés par le Brief (défauts = comportement historique).
_PLATFORM_LABELS = {
    "tiktok": "TikTok",
    "reels": "Reels",
    "shorts": "Shorts",
    "youtube_short": "YouTube Shorts",
}
_LANG_LABELS = {"fr": "FRENCH", "en": "ENGLISH", "es": "SPANISH", "de": "GERMAN"}


def _platform_label(platform: str) -> str:
    return _PLATFORM_LABELS.get(platform, "TikTok/Reels/Shorts")


def _lang_label(language: str) -> str:
    return _LANG_LABELS.get(language, language.upper() or "FRENCH")


# -- modèles de PARSE (lenient : le LLM peut ajouter des clés) ----------------
# Mirroir des sous-modèles v5 ; mappés vers les modèles stricts ensuite.

class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _LumOut(_Lenient):
    sources: LooseStr = ""
    direction: LooseStr = ""
    qualite: LooseStr = ""
    temperature: LooseStr = ""
    contraste: LooseStr = ""


class _LocOut(_Lenient):
    lieu: LooseStr = ""
    echelle: LooseStr = ""
    int_ext: LooseStr = ""
    layout_spatial: LooseStr = ""
    palette: LooseStr = ""
    matieres: LooseStr = ""
    props_fixes: list[str] = []
    lumiere_base: _LumOut = _LumOut()


class _SceneSk(_Lenient):
    id: LooseStr = ""
    title: LooseStr = ""
    environment_desc: LooseStr = ""       # prompt de la photo d'établissement (EN)
    intention: LooseStr = ""
    location: _LocOut = _LocOut()    # le décor structuré (bible)
    saison: LooseStr = ""
    moment_jour: LooseStr = ""
    meteo: LooseStr = ""
    lumiere_ambiante: _LumOut = _LumOut()
    mood: LooseStr = ""
    ambiance_sonore: LooseStr = ""


class _CharBibleOut(_Lenient):
    name: LooseStr = ""
    appearance: LooseStr = ""
    wardrobe: LooseStr = ""
    voice_id: LooseStr = ""
    traits: LooseStr = ""


class _ScenesOut(_Lenient):
    scenes: list[_SceneSk] = []
    characters: list[_CharBibleOut] = []   # la bible perso (identités récurrentes)
    musique_score: LooseStr = ""
    genre: LooseStr = ""
    ton: LooseStr = ""


class _CadreOut(_Lenient):
    taille_plan: LooseStr = ""
    focale: LooseStr = ""
    angle_hauteur: LooseStr = ""
    mise_au_point: LooseStr = ""


class _CamOut(_Lenient):
    type: LooseStr = ""
    vitesse: LooseStr = ""
    depart_arrivee: LooseStr = ""


class _PersOut(_Lenient):
    name: LooseStr = ""
    action: LooseStr = ""
    trajectoire: LooseStr = ""
    vitesse: LooseStr = ""
    expression: LooseStr = ""
    etat_debut: LooseStr = ""
    etat_fin: LooseStr = ""


class _ElemOut(_Lenient):
    quoi: LooseStr = ""
    mouvement: LooseStr = ""
    etat_debut: LooseStr = ""
    etat_fin: LooseStr = ""


class _PhysOut(_Lenient):
    element: LooseStr = ""
    comportement: LooseStr = ""
    intensite_direction: LooseStr = ""


class _LtOut(_Lenient):
    ce_qui_change: LooseStr = ""
    depart_arrivee: LooseStr = ""


class _SonOut(_Lenient):
    dialogue_voix: LooseStr = ""
    bruitage_sfx: LooseStr = ""


class _ShotOut(_Lenient):
    id: LooseStr = ""
    kind: str = "video"
    narration_fr: LooseStr = ""
    duration_s: float = 4.0
    start_image: LooseStr = ""
    intention_plan: LooseStr = ""
    cadre: _CadreOut = _CadreOut()
    profondeur: dict[str, str] = {}
    camera: _CamOut = _CamOut()
    personnages: list[_PersOut] = []
    elements_secondaires: list[_ElemOut] = []
    physique_environnement: list[_PhysOut] = []
    lumiere_temps: _LtOut = _LtOut()
    son: _SonOut = _SonOut()


class _ShotsOut(_Lenient):
    shots: list[_ShotOut] = []


def _kind_of(raw: str) -> Literal["video", "photo"]:
    return "photo" if raw.strip().lower() == "photo" else "video"


def _lum(o: _LumOut) -> Lumiere:
    return Lumiere(sources=o.sources, direction=o.direction, qualite=o.qualite,
                   temperature=o.temperature, contraste=o.contraste)


def _shot_of(s: _ShotOut, fallback_id: str) -> ShotPlan:
    """Mappe un plan parsé (lenient) → `ShotPlan` (sous-modèles v5 stricts)."""
    prof = s.profondeur or {}
    return ShotPlan(
        id=s.id or fallback_id, kind=_kind_of(s.kind),
        duree_s=max(2.0, min(6.0, s.duration_s or 4.0)),
        narration_fr=s.narration_fr or s.son.dialogue_voix,
        start_image=s.start_image,
        cadre=Cadre(taille_plan=s.cadre.taille_plan, focale=s.cadre.focale,
                    angle_hauteur=s.cadre.angle_hauteur, mise_au_point=s.cadre.mise_au_point),
        profondeur=Profondeur(avant_plan=prof.get("avant_plan", ""),
                              plan_moyen=prof.get("plan_moyen", ""),
                              arriere_plan=prof.get("arriere_plan", "")),
        camera=Camera(type=s.camera.type, vitesse=s.camera.vitesse,
                      depart_arrivee=s.camera.depart_arrivee),
        personnages=[ShotCharacterPlan(name=p.name, action=p.action, trajectoire=p.trajectoire,
                     vitesse=p.vitesse, expression=p.expression,
                     etat_debut=p.etat_debut, etat_fin=p.etat_fin) for p in s.personnages],
        elements_secondaires=[ElementSecondaire(quoi=e.quoi, mouvement=e.mouvement,
                              etat_debut=e.etat_debut, etat_fin=e.etat_fin)
                              for e in s.elements_secondaires],
        physique_environnement=[Physique(element=p.element, comportement=p.comportement,
                                intensite_direction=p.intensite_direction)
                                for p in s.physique_environnement],
        lumiere_temps=LumiereTemps(ce_qui_change=s.lumiere_temps.ce_qui_change,
                                   depart_arrivee=s.lumiere_temps.depart_arrivee),
        son=Son(dialogue_voix=s.son.dialogue_voix, bruitage_sfx=s.son.bruitage_sfx),
        intention_plan=s.intention_plan,
    )


def _location_of(sk: _SceneSk, ref: str) -> LocationEntry:
    """Le décor structuré d'une scène → une fiche `LocationEntry` (bible décor)."""
    lo = sk.location
    return LocationEntry(
        ref=ref, lieu=lo.lieu or sk.environment_desc, echelle=lo.echelle, int_ext=lo.int_ext,
        layout_spatial=lo.layout_spatial, palette=lo.palette, matieres=lo.matieres,
        props_fixes=lo.props_fixes, lumiere_base=_lum(lo.lumiere_base),
    )


class OpenAISceneDecomposer:
    """Implémente `SceneVideoDecomposer` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def _chat_json(self, system: str, user: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # erreur réseau / API (clé invalide, modèle inconnu, quotas…)
            raise SceneDecompositionError(
                "L'appel au décrypteur OpenAI a échoué "
                "(vérifie ta clé, le modèle OPENAI_MODEL et tes quotas). "
                f"Détail : {e}"
            ) from e
        content: str = resp.choices[0].message.content or ""
        return content

    def _plan_scenes(
        self,
        prompt: str,
        style_identity: str,
        n_scenes: int,
        *,
        platform: str,
        language: str,
    ) -> _ScenesOut:
        """MACRO : l'arc (scènes + DÉCOR structuré + variation) + la bible perso."""
        lang = _lang_label(language)
        system = (
            f"You are a short-form vertical (9:16) video director for {_platform_label(platform)}. "
            "Plan a video as an ORDERED list of SCENES forming a tight arc: HOOK, BUILD, PAYOFF. "
            "A SCENE is ONE concentrated context — a single LOCATION and moment. Reusable ASSETS "
            "(locations, characters) are defined ONCE and referenced.\n"
            "Return JSON (ENGLISH for all visual fields, image models expect English):\n"
            f'{{"genre","ton","musique_score",'
            '"characters":[{"name"(FRENCH first name),"appearance"(physical, EN),"wardrobe"(EN),'
            '"voice_id","traits"}],'
            f'"scenes":[  // EXACTLY {n_scenes}\n'
            '  {"id","title"(' + lang + '),'
            '"environment_desc"(EN still-photo prompt of the empty set: place, textures, mood; NO text/watermark),'
            '"intention"(what happens & why it matters, ' + lang + '),'
            '"location":{"lieu","echelle","int_ext","layout_spatial"(what is where, framing-independent),'
            '"palette","matieres","props_fixes":[...],'
            '"lumiere_base":{"sources","direction","qualite","temperature","contraste"}},'
            '"saison","moment_jour","meteo","mood","ambiance_sonore"(room tone),'
            '"lumiere_ambiante":{"sources","direction","qualite","temperature","contraste"}}'
            "]}\n"
            "Two scenes in the SAME place must reuse the SAME location description. "
            "A character keeps the SAME appearance across scenes. Output JSON only."
        )
        if style_identity.strip():
            system += f"\nSTYLE / IDENTITY (apply throughout): {style_identity.strip()}"
        user = f"Idea / pitch: {prompt}\nPlan EXACTLY {n_scenes} scenes now."
        try:
            return _ScenesOut.model_validate_json(self._chat_json(system, user))
        except ValidationError:
            return _ScenesOut()

    def _expand_scene(
        self,
        sk: _SceneSk,
        style_identity: str,
        running_summary: str,
        *,
        language: str,
        scene_budget_s: float,
    ) -> list[ShotPlan]:
        """MICRO : la scène → plans COURTS (1 prise i2v = état début → état fin)."""
        lang = _lang_label(language)
        system = (
            "You are a director breaking ONE scene into SHORT shots (3 to 5 s). Each shot is "
            "ONE continuous i2v take: a start frame that INTERPOLATES to an end state, INSIDE "
            "the scene's location (never cut to a new place). Don't re-describe the location or "
            "characters' appearance (inherited) — describe only what is PROPER to this take.\n"
            f'Return JSON {{"shots":[...]}} with 2 to {_MAX_SHOTS} shots (ENGLISH visuals), each:\n'
            '- "id","kind":"video"|"photo","duration_s":3-5;\n'
            '- "start_image": the composed starting frame (subject placement within the location);\n'
            '- "cadre":{"taille_plan"(wide…extreme close),"focale"(24/50/85mm),'
            '"angle_hauteur"(eye/high/low),"mise_au_point"};\n'
            '- "profondeur":{"avant_plan","plan_moyen","arriere_plan"};\n'
            '- "camera":{"type"(STRICTLY STATIC unless truly needed: static/slow push),"vitesse",'
            '"depart_arrivee"(how the frame starts→ends)};\n'
            '- "personnages":[{"name"(FRENCH first name, from the bible),"action","trajectoire",'
            '"vitesse","expression","etat_debut","etat_fin"}] — the interpolation début→fin;\n'
            '- "elements_secondaires":[{"quoi","mouvement","etat_debut","etat_fin"}] (hair, cloth, sign…);\n'
            '- "physique_environnement":[{"element","comportement","intensite_direction"}] (wind, snow…);\n'
            '- "lumiere_temps":{"ce_qui_change","depart_arrivee"} (light change WITHIN the take);\n'
            '- "son":{"dialogue_voix"(' + lang + ', one short spoken line),"bruitage_sfx"(synced)};\n'
            f'- "narration_fr": {lang} (same as son.dialogue_voix if spoken);\n'
            '- "intention_plan": what THIS take tells.\n'
            "The FIRST shot hooks. No on-screen text. Output JSON only."
        )
        if scene_budget_s > 0:
            system += (
                f"\nAim for a TOTAL of about {scene_budget_s:.0f}s of footage across this "
                "scene's shots (pick the shot count and durations to fit that budget)."
            )
        if style_identity.strip():
            system += f"\nSTYLE / IDENTITY: {style_identity.strip()}"
        user = (
            f"Scene: {sk.title}\nEnvironment: {sk.environment_desc}\n"
            f"Intention: {sk.intention}\nStory so far: {running_summary or '(start)'}\n"
            "Break this scene into short shots now."
        )
        try:
            out = _ShotsOut.model_validate_json(self._chat_json(system, user))
        except ValidationError:
            return []
        return [
            _shot_of(s, f"{sk.id or 'sc'}_sh{i + 1}")
            for i, s in enumerate(out.shots[:_MAX_SHOTS])
        ]

    def plan_arc(
        self,
        prompt: str,
        *,
        style_identity: LooseStr = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
    ) -> list[ScenePlan]:
        n = max(1, n_scenes)
        macro = self._plan_scenes(
            prompt, style_identity, n, platform=platform, language=language
        )
        if not macro.scenes:
            raise SceneDecompositionError(
                "L'IA n'a pas pu découper cette idée en scènes. Reformule ton idée "
                "ou réessaie."
            )
        return [
            ScenePlan(
                id=sk.id or f"s{i + 1}",
                title=sk.title or f"Scène {i + 1}",
                environment_desc=sk.environment_desc,
                location_ref=f"{sk.id or f's{i + 1}'}_loc",
                saison=sk.saison, moment_jour=sk.moment_jour, meteo=sk.meteo,
                lumiere_ambiante=_lum(sk.lumiere_ambiante), mood=sk.mood,
                ambiance_sonore=sk.ambiance_sonore, intention_scene=sk.intention,
            )
            for i, sk in enumerate(macro.scenes[:n])
        ]

    def decompose_video(
        self,
        prompt: str,
        *,
        style_identity: LooseStr = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
        target_duration_s: float = 0.0,
    ) -> VideoPlan:
        n = max(1, n_scenes)
        macro = self._plan_scenes(
            prompt, style_identity, n, platform=platform, language=language
        )
        if not macro.scenes:
            raise SceneDecompositionError(
                "L'IA n'a pas pu découper cette idée en scènes. Reformule ton idée "
                "ou réessaie."
            )
        # Budget-temps par scène (réparti) quand une durée cible est fournie.
        scene_budget = target_duration_s / n if target_duration_s > 0 else 0.0
        scenes: list[ScenePlan] = []
        locations: list[LocationEntry] = []
        summary_parts: list[str] = []
        for i, sk in enumerate(macro.scenes[:n]):
            sid = sk.id or f"s{i + 1}"
            shots = self._expand_scene(
                sk, style_identity, " ".join(summary_parts),
                language=language, scene_budget_s=scene_budget,
            )
            if not shots:
                # Micro illisible : plan minimal qui anime l'établissement (scène vivante).
                shots = [ShotPlan(id=f"{sid}_sh1", kind="video", duree_s=4.0,
                                  start_image=sk.environment_desc,
                                  camera=Camera(depart_arrivee="slow push in, static camera"))]
            loc_ref = f"{sid}_loc"
            locations.append(_location_of(sk, loc_ref))
            scenes.append(
                ScenePlan(
                    id=sid, title=sk.title or f"Scène {i + 1}",
                    environment_desc=sk.environment_desc, location_ref=loc_ref,
                    saison=sk.saison, moment_jour=sk.moment_jour, meteo=sk.meteo,
                    lumiere_ambiante=_lum(sk.lumiere_ambiante), mood=sk.mood,
                    ambiance_sonore=sk.ambiance_sonore, intention_scene=sk.intention,
                    shots=shots,
                )
            )
            if sk.intention:
                summary_parts.append(sk.intention)
        return VideoPlan(
            title=prompt[:60] or "Nouvelle vidéo",
            meta=RenderMeta(style_rendu=style_identity),
            intention_globale=IntentionGlobale(
                genre=macro.genre, ton=macro.ton, arc_narratif=prompt),
            musique_score=macro.musique_score,
            location_bible=locations,
            cast=[CharacterPlan(name=c.name, appearance=c.appearance, wardrobe=c.wardrobe,
                                voice_id=c.voice_id, traits=c.traits)
                  for c in macro.characters if c.name.strip()],
            scenes=scenes,
        )
