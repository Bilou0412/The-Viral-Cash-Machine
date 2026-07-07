"""Moteur de la table ronde — la boucle de discussion d'UNE scène.

Déterministe dans l'ordre : à chaque tour, chaque voix parle en voyant le débat
en cours (le transcript grandit), puis le synthétiseur en extrait la scène
structurée. Aucun aléatoire (l'ordre des voix EST la structure du débat).
"""

from __future__ import annotations

from ..brief.model import Brief
from .model import RoomMemory, RoomResult, SceneBrief, Turn
from .ports import ROOM_VOICES, RoomVoice, SceneSynthesizer


def run_scene_room(
    brief: Brief,
    scene_brief: SceneBrief,
    memory: RoomMemory,
    *,
    voices: RoomVoice,
    synthesizer: SceneSynthesizer,
    rounds: int = 2,
    voice_order: tuple[str, ...] = ROOM_VOICES,
) -> RoomResult:
    """La table ronde crée une scène : `rounds` tours de débat, puis synthèse.

    `voices` dispatche par rôle (une impl unique), `synthesizer` lit le débat.
    Renvoie la scène structurée + les persos neufs + le transcript complet.
    """
    transcript: list[Turn] = []
    for _ in range(max(1, rounds)):
        for role in voice_order:
            message = voices.speak(
                role=role, brief=brief, scene_brief=scene_brief,
                memory=memory, transcript=transcript,
            )
            if message.strip():
                transcript.append(Turn(role=role, message=message.strip()))
    result = synthesizer.synthesize(
        brief=brief, scene_brief=scene_brief, memory=memory, transcript=transcript
    )
    # Le transcript du débat est la source de vérité (le synthétiseur ne le refait pas).
    return result.model_copy(update={"transcript": transcript})
