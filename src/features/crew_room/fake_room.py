"""Atelier FAKE — déterministe, hors-ligne (dev + tests).

Réalisateur canné (pose un contrat de 2 plans) + départements cannés (chacun
remplit SES trous). Déterministe → golden offline, sans réseau.
"""

from __future__ import annotations

from ..brief.model import Brief
from ..scenes.model import CharacterPlan, ScenePlan, ShotCharacterPlan
from .model import (
    ContractShot,
    Draft,
    ReviewVerdict,
    RoomMemory,
    SceneBrief,
    SceneContract,
)

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
                        name=hero.name,
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

    def revise(
        self,
        *,
        department: str,
        scene: ScenePlan,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
        note: str = "",
    ) -> Draft:
        """2e passe informée. Par défaut, le brouillon est inchangé (idempotent).
        Exemple de cohérence croisée : le DIALOGUISTE voit qui le casting a placé
        sur chaque plan et **nomme le personnage** dans la narration. `note` (consigne
        du superviseur) est acceptée puis ignorée par le Fake (déterministe)."""
        base = self.fill(
            department=department, contract=contract,
            brief=brief, scene_brief=scene_brief, memory=memory,
        )
        if department != "dialoguiste":
            return base
        shots: dict[str, dict[str, str]] = {}
        for sh in scene.shots:
            line = base.shots.get(sh.id, {}).get("narration", "") or sh.narration_fr
            who = sh.personnages[0].name if sh.personnages else ""
            shots[sh.id] = {"narration": f"{who} — {line}" if who else line}
        return Draft(department=department, shots=shots)


class FakeReviewer:
    """Implémente `Reviewer` sans réseau. Déterministe et TERMINANT (par le contenu) :
    tant que le dialoguiste n'a pas nommé le personnage placé par le casting sur le 1er
    plan, le superviseur le renvoie corriger ; sinon il valide. Illustre la boucle réelle
    (le débat) tout en garantissant la convergence offline."""

    def review(
        self,
        *,
        scene: ScenePlan,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> ReviewVerdict:
        first = scene.shots[0] if scene.shots else None
        who = first.personnages[0].name if first and first.personnages else ""
        if who and first is not None and who not in first.narration_fr:
            return ReviewVerdict(
                ok=False,
                redo={"dialoguiste": "Nomme le personnage présent dans la narration."},
                note="Incohérence dialogue/casting : le perso placé n'est pas nommé.",
            )
        return ReviewVerdict(ok=True, note="Scène cohérente, validée.")
