"""Table ronde FAKE — déterministe, hors-ligne (dev + tests).

Voix cannée par métier (référence brief/scène/mémoire) + synthétiseur qui pond
une scène STRUCTURÉE (format v4) déterministe. Sert de défaut offline et de
golden. Aucune I/O, aucun réseau.
"""

from __future__ import annotations

from ..brief.model import Brief
from ..scenes.model import CharacterPlan, ScenePlan, ShotCharacterPlan, ShotPlan
from .model import RoomMemory, RoomResult, SceneBrief, Turn

_HERO = CharacterPlan(
    name="Léa",
    appearance="young woman, early 20s, short dark hair, pale skin",
    wardrobe="worn grey wool coat",
    voice_id="Deep_Voice_Man",
    traits="déterminée, méfiante",
)


def _hero_of(memory: RoomMemory) -> tuple[CharacterPlan, bool]:
    """Le protagoniste : celui de la bible s'il existe, sinon on l'introduit (neuf)."""
    if memory.bible:
        return memory.bible[0], False
    return _HERO, True


class FakeRoomVoice:
    """Implémente `RoomVoice` sans réseau : un message déterministe par métier."""

    def speak(
        self,
        *,
        role: str,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
        transcript: list[Turn],
    ) -> str:
        hero, _ = _hero_of(memory)
        title = scene_brief.title or "cette scène"
        second = any(t.role == role for t in transcript)  # 2e tour de ce métier ?
        if role == "realisateur":
            if second:
                return f"OK, on verrouille {title}. Ton {brief.ton or 'tendu'}, on garde le rythme."
            return (
                f"On ouvre sur « {title} ». Intention : {scene_brief.intention or 'faire monter la tension'}. "
                f"Objectif produit : {brief.objectif or 'accrocher'}."
            )
        if role == "directeur_artistique":
            return (
                f"Décor : {scene_brief.environment or f'le lieu de {title}'}, lumière froide et dure. "
                "On reste dans l'identité visuelle établie."
            )
        if role == "chef_operateur":
            return "Deux plans : un large d'accroche puis un plan serré sur la réaction. Caméra fixe."
        if role == "casting":
            if memory.bible:
                return f"{hero.name} est présente, {hero.wardrobe}. On garde sa continuité."
            return f"On introduit {hero.name} : {hero.appearance}, {hero.wardrobe}."
        if role == "dialoguiste":
            return f"Narration courte, en français : une phrase qui installe « {title} »."
        return ""


class FakeSceneSynthesizer:
    """Implémente `SceneSynthesizer` : extrait une scène structurée déterministe."""

    def synthesize(
        self,
        *,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
        transcript: list[Turn],
    ) -> RoomResult:
        hero, is_new = _hero_of(memory)
        sid = scene_brief.id or "s1"
        decor = scene_brief.environment or f"the location of {scene_brief.title or 'the scene'}"
        env = scene_brief.environment or f"wide establishing shot of {scene_brief.title or 'the scene'}"

        def char(expression: str, action: str) -> ShotCharacterPlan:
            return ShotCharacterPlan(
                name=hero.name, appearance=hero.appearance,
                wardrobe=hero.wardrobe, expression=expression, action=action,
            )

        scene = ScenePlan(
            id=sid,
            title=scene_brief.title or "Scène",
            environment_desc=env,
            lighting="cold ambient light",
            context_text=scene_brief.intention,
            art_direction="cold tones, film grain",
            shots=[
                ShotPlan(
                    id=f"{sid}_sh1", kind="video",
                    visual_desc=f"wide shot inside {decor}",
                    motion_desc="slow push in, static camera",
                    narration_fr="La tension monte.", duration_s=4.0,
                    decor=decor, lighting="cold ambient light", framing="wide shot",
                    characters=[char("tense", "observing the space")],
                ),
                ShotPlan(
                    id=f"{sid}_sh2", kind="video",
                    visual_desc=f"close reaction inside {decor}",
                    motion_desc="static framing", narration_fr="Un choix s'impose.",
                    duration_s=4.0, decor=decor, lighting="cold ambient light",
                    framing="close-up", characters=[char("resolute", "deciding")],
                ),
            ],
        )
        return RoomResult(scene=scene, new_characters=[hero] if is_new else [])
