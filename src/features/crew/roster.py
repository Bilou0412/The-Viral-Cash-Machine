"""Le casting du studio — la liste des agents-métiers par phase.

Source unique de vérité pour la « salle de production » (l'UI) : qui fait quoi,
à quelle phase, et par quel moteur (le décrypteur existant, la génération, le
rendu, ou un agent dédié). Le front en tient un miroir (`lib/crew.ts`).

Phases (colonne vertébrale du cinéma) :
développement → préproduction → tournage → postproduction → distribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Phase = Literal[
    "developpement",
    "preproduction",
    "tournage",
    "postproduction",
    "distribution",
]

# Ce qui exécute le métier : le producteur (brief), le décrypteur existant, la
# génération d'assets, le rendu, ou un agent dédié (aujourd'hui : distribution).
AgentKind = Literal["brief", "decomposer", "generation", "render", "distribution"]


@dataclass(frozen=True)
class CrewRole:
    """Un membre de l'équipe : un métier tenu par un agent."""

    key: str
    phase: Phase
    title: str      # nom ciné du métier
    subtitle: str   # ce qu'il fait, côté créateur
    produces: str   # son artefact
    kind: AgentKind


PHASES: tuple[Phase, ...] = (
    "developpement",
    "preproduction",
    "tournage",
    "postproduction",
    "distribution",
)

CREW: tuple[CrewRole, ...] = (
    CrewRole(
        key="producteur",
        phase="developpement",
        title="Producteur",
        subtitle="cadre le brief : objectif, audience, plateforme, durée, coût",
        produces="le brief",
        kind="brief",
    ),
    CrewRole(
        key="scenariste",
        phase="developpement",
        title="Scénariste",
        subtitle="transforme l'idée en découpage de scènes",
        produces="le découpage (scènes)",
        kind="decomposer",
    ),
    CrewRole(
        key="directeur_artistique",
        phase="preproduction",
        title="Directeur artistique",
        subtitle="pose l'identité visuelle et la photo d'environnement",
        produces="le storyboard (décors)",
        kind="decomposer",
    ),
    CrewRole(
        key="chef_operateur",
        phase="preproduction",
        title="Chef opérateur",
        subtitle="découpe chaque scène en plans (cadrage, mouvement)",
        produces="les plans",
        kind="decomposer",
    ),
    CrewRole(
        key="dialoguiste",
        phase="preproduction",
        title="Dialoguiste",
        subtitle="écrit la narration et les dialogues",
        produces="la narration",
        kind="decomposer",
    ),
    CrewRole(
        key="tournage",
        phase="tournage",
        title="Équipe de tournage",
        subtitle="exécute les prompts et capte les prises",
        produces="les rushes (images/vidéos)",
        kind="generation",
    ),
    CrewRole(
        key="monteur",
        phase="postproduction",
        title="Monteur",
        subtitle="assemble les plans et règle le rythme",
        produces="le montage",
        kind="render",
    ),
    CrewRole(
        key="inge_son",
        phase="postproduction",
        title="Ingé son",
        subtitle="habille la voix et le son",
        produces="l'habillage sonore",
        kind="render",
    ),
    CrewRole(
        key="attache_presse",
        phase="distribution",
        title="Attaché de presse",
        subtitle="écrit titre, description, hashtags et hook",
        produces="la fiche de sortie",
        kind="distribution",
    ),
)


def roster() -> list[dict[str, str]]:
    """Le casting sérialisable (pour l'API / l'UI)."""
    return [
        {
            "key": r.key,
            "phase": r.phase,
            "title": r.title,
            "subtitle": r.subtitle,
            "produces": r.produces,
            "kind": r.kind,
        }
        for r in CREW
    ]
