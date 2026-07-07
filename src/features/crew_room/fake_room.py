"""Atelier FAKE — déterministe, hors-ligne (dev + tests).

Réalisateur canné (pose un contrat de 2 plans) + départements cannés (chacun
remplit SES trous). Déterministe → golden offline, sans réseau.
"""

from __future__ import annotations

from ..brief.model import Brief
from ..scenes.model import CharacterPlan, ShotCharacterPlan
from .model import ContractShot, Draft, RoomMemory, SceneBrief, SceneContract

_HERO = CharacterPlan(
    name="Léa",
    appearance="young woman, early 20s, short dark hair, pale skin",
    wardrobe="worn grey wool coat",
    voice_id="Deep_Voice_Man",
    traits="déterminée, méfiante",
)


def _hero_of(memory: RoomMemory) -> tuple[CharacterPlan, bool]:
    if memory.bible:
        return memory.bible[0], False
    return _HERO, True


class FakeContractAgent:
    """Implémente `ContractAgent` : un contrat déterministe de 2 plans."""

    def define(
        self, *, brief: Brief, scene_brief: SceneBrief, memory: RoomMemory
    ) -> SceneContract:
        sid = scene_brief.id or "s1"
        return SceneContract(
            env_intention=scene_brief.environment or f"le lieu de {scene_brief.title}",
            shots=[
                ContractShot(id=f"{sid}_sh1", beat="plan d'accroche", kind="video"),
                ContractShot(id=f"{sid}_sh2", beat="plan de réaction", kind="video"),
            ],
        )


class FakeDrafter:
    """Implémente `Drafter` : chaque département remplit SON brouillon (déterministe)."""

    def fill(
        self,
        *,
        department: str,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> Draft:
        ids = [cs.id for cs in contract.shots]
        decor = scene_brief.environment or f"the location of {scene_brief.title or 'the scene'}"

        if department == "directeur_artistique":
            return Draft(
                department=department,
                env={"decor": decor, "lighting": "cold ambient light"},
                shots={i: {"decor": f"inside {decor}", "lighting": "cold ambient light"} for i in ids},
            )
        if department == "chef_operateur":
            framings = ["wide shot", "close-up", "medium POV shot", "over-the-shoulder"]
            return Draft(
                department=department,
                shots={
                    i: {"framing": framings[k % len(framings)], "duration": "4"}
                    for k, i in enumerate(ids)
                },
            )
        if department == "casting":
            hero, is_new = _hero_of(memory)
            plays = [("tense", "observing the space"), ("resolute", "deciding")]
            return Draft(
                department=department,
                new_characters=[hero] if is_new else [],
                shot_characters={
                    i: [ShotCharacterPlan(
                        name=hero.name, appearance=hero.appearance, wardrobe=hero.wardrobe,
                        expression=plays[k % len(plays)][0], action=plays[k % len(plays)][1],
                    )]
                    for k, i in enumerate(ids)
                },
            )
        if department == "dialoguiste":
            lines = ["La tension monte.", "Un choix s'impose."]
            return Draft(
                department=department,
                shots={i: {"narration": lines[k % len(lines)]} for k, i in enumerate(ids)},
            )
        return Draft(department=department)
