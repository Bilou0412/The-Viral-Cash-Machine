"""Décrypteur de scènes FAKE — déterministe, hors-ligne (dev + tests).

Ignore le prompt (pas de réseau) : produit un exemple **3 niveaux richement rempli**
(Vidéo → Scène → Plan) — bibles décor+perso, scène qui référence un décor et le fait
varier, plans détaillés (cadre, caméra, action début→fin, physique, son). Sert de
défaut offline et de golden, et instancie le template pour l'aperçu `--text`.
"""

from __future__ import annotations

from ...editor.document import (
    Cadre,
    Camera,
    ElementSecondaire,
    IntentionGlobale,
    LocationEntry,
    Lumiere,
    LumiereTemps,
    Physique,
    RenderMeta,
    Son,
)
from .model import CharacterPlan, ScenePlan, ShotCharacterPlan, ShotPlan, VideoPlan
from .ports import DEFAULT_SCENES

_HERO = CharacterPlan(
    name="Léa", appearance="young woman, short dark hair", wardrobe="worn grey coat",
    voice_id="Deep_Voice_Man", traits="determined, wary",
)

_META = RenderMeta(
    ratio="9:16", fps=30, resolution="1080p",
    style_rendu="photorealistic cinematic", grain_etalonnage="subtle grain, cold contrast",
)


def _location(n: int) -> LocationEntry:
    return LocationEntry(
        ref=f"loc{n}", lieu=f"deserted subway platform (location {n})", echelle="vast",
        int_ext="interior", layout_spatial="long platform, rails on the left, benches on the right",
        palette="cold blues and white neon", matieres="tiles, concrete, metal",
        props_fixes=["benches", "signage", "neon lights"],
        lumiere_base=Lumiere(sources="neon", direction="overhead", qualite="hard",
                             temperature="cold", contraste="high-contrast"),
    )


def _scene(n: int) -> ScenePlan:
    return ScenePlan(
        id=f"s{n}", title=f"Scène {n}",
        environment_desc=f"wide establishing shot of deserted subway platform {n}, cold neon, cinematic",
        location_ref=f"loc{n}",
        saison="hiver", moment_jour="2am", meteo="dry",
        lumiere_ambiante=Lumiere(sources="flickering neon", direction="overhead", qualite="hard",
                                 temperature="cold", contraste="high-contrast"),
        mood="uneasy, tense", ambiance_sonore="low hum of neon, distant train rumble",
        intention_scene="installer le malaise avant le basculement",
        shots=[
            ShotPlan(
                id=f"s{n}_sh1", kind="video", duree_s=3.0, narration_fr="La tension monte.",
                start_image="Léa alone on the empty platform, seen from afar",
                cadre=Cadre(taille_plan="wide shot", focale="35mm", angle_hauteur="eye level"),
                camera=Camera(type="slow push in", vitesse="slow", depart_arrivee="from wide to medium"),
                personnages=[ShotCharacterPlan(
                    name="Léa", action="scanning the platform", trajectoire="stays center",
                    vitesse="still", expression="tense", etat_debut="frozen", etat_fin="turns her head")],
                physique_environnement=[Physique(element="neon", comportement="flickering",
                                                 intensite_direction="irregular, overhead")],
                intention_plan="montrer sa solitude",
            ),
            ShotPlan(
                id=f"s{n}_sh2", kind="video", duree_s=4.0, narration_fr="Un choix s'impose.",
                start_image="close-up on Léa's face, neon reflecting in her eyes",
                cadre=Cadre(taille_plan="close-up", focale="85mm", angle_hauteur="slightly low"),
                camera=Camera(type="static", vitesse="none", depart_arrivee="locked framing"),
                personnages=[ShotCharacterPlan(
                    name="Léa", action="steeling herself, then deciding", trajectoire="none",
                    vitesse="still", expression="resolute", etat_debut="hesitant", etat_fin="determined")],
                elements_secondaires=[ElementSecondaire(quoi="her hair", mouvement="stirred by a draft",
                                                        etat_debut="still", etat_fin="lifted")],
                lumiere_temps=LumiereTemps(ce_qui_change="a neon buzzes and dims",
                                           depart_arrivee="from lit to half-dark"),
                son=Son(dialogue_voix="Un choix s'impose.", bruitage_sfx="neon buzz, faint breath"),
                intention_plan="le basculement intérieur",
            ),
        ],
    )


class FakeSceneDecomposer:
    """Implémente `SceneVideoDecomposer` sans appel réseau (exemple 3-niveaux)."""

    def decompose_video(
        self,
        prompt: str,
        *,
        style_identity: str = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
        target_duration_s: float = 0.0,
    ) -> VideoPlan:
        # Déterministe/offline : les paramètres du Brief sont acceptés puis ignorés.
        count = max(1, n_scenes)
        return VideoPlan(
            title="Vidéo générée",
            meta=_META,
            intention_globale=IntentionGlobale(
                genre="thriller court", ton="tendu",
                arc_narratif=prompt or "une courte vidéo verticale, montée de tension",
            ),
            musique_score="nappe sombre, tension sourde",
            location_bible=[_location(i + 1) for i in range(count)],
            cast=[_HERO],
            scenes=[_scene(i + 1) for i in range(count)],
        )

    def plan_arc(
        self,
        prompt: str,
        *,
        style_identity: str = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
    ) -> list[ScenePlan]:
        # Squelettes déterministes (sans plans) — la table ronde les remplira.
        beats = ["Accroche", "Montée", "Chute"]
        return [
            ScenePlan(
                id=f"s{i + 1}",
                title=f"Scène {i + 1} — {beats[i] if i < len(beats) else 'Suite'}",
                environment_desc=f"establishing shot of location {i + 1}, cinematic",
                location_ref=f"loc{i + 1}",
                intention_scene=f"Le contexte concentré de la scène {i + 1}.",
            )
            for i in range(max(1, n_scenes))
        ]
