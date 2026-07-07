"""Mise en commun — assemble les brouillons des départements en une scène.

Chaque champ est pioché chez son département PROPRIÉTAIRE (`field_owner`) : comme
les trous sont disjoints, l'assemblage est purement mécanique (aucun conflit). Le
résultat est un `ScenePlan` structuré (format v4) + les persos neufs + un
transcript lisible (le contrat, puis chaque brouillon).
"""

from __future__ import annotations

from ..scenes.model import ScenePlan, ShotPlan
from .model import Draft, RoomResult, SceneBrief, SceneContract, Turn
from .ports import DEPARTMENTS, field_owner


def _clamp_duration(raw: str) -> float:
    try:
        return max(2.0, min(6.0, float(raw)))
    except (TypeError, ValueError):
        return 4.0


def _field(drafts: dict[str, Draft], shot_id: str, field: str) -> str:
    """La valeur d'un champ pour un plan, piochée chez son propriétaire."""
    owner = field_owner(field)
    return drafts.get(owner, Draft()).shots.get(shot_id, {}).get(field, "")


def _draft_summary(d: Draft) -> str:
    """Un résumé lisible d'un brouillon (pour le transcript / l'UI)."""
    if d.department == "directeur_artistique":
        env = ", ".join(v for v in (d.env.get("decor", ""), d.env.get("lighting", "")) if v)
        return f"Décor & lumière — env: {env or '(?)'} ; {len(d.shots)} plans habillés."
    if d.department == "chef_operateur":
        cad = "; ".join(s.get("framing", "") for s in d.shots.values() if s.get("framing"))
        return f"Cadrage — {cad or '(?)'}."
    if d.department == "casting":
        who = ", ".join(c.name for c in d.new_characters) or "(bible réutilisée)"
        return f"Personnages — nouveaux: {who}."
    if d.department == "dialoguiste":
        lines = " / ".join(s.get("narration", "") for s in d.shots.values() if s.get("narration"))
        return f"Narration — {lines or '(?)'}."
    return d.department


def contract_turn(contract: SceneContract) -> Turn:
    """Le tour « réalisateur » : la scène à trous (les plans + leurs beats)."""
    beats = ", ".join(f"{cs.id}: {cs.beat}" for cs in contract.shots)
    return Turn(role="realisateur", message=f"Contrat de scène — {len(contract.shots)} plans ({beats}).")


def draft_turns(drafts: list[Draft], *, label: str = "") -> list[Turn]:
    """Un tour par département (dans l'ordre `DEPARTMENTS`), résumé de son brouillon.
    `label` (« brouillon » / « révision ») préfixe le message pour distinguer les passes."""
    by_dept = {d.department: d for d in drafts}
    prefix = f"{label.capitalize()} · " if label else ""
    return [
        Turn(role=dept, message=f"{prefix}{_draft_summary(d)}")
        for dept in DEPARTMENTS
        if (d := by_dept.get(dept)) is not None
    ]


def merge_drafts(
    scene_brief: SceneBrief, contract: SceneContract, drafts: list[Draft]
) -> RoomResult:
    """Assemble les brouillons en une scène structurée (chaque champ chez son propriétaire)."""
    by_dept = {d.department: d for d in drafts}
    da = by_dept.get("directeur_artistique", Draft())
    casting = by_dept.get("casting", Draft())
    sid = scene_brief.id or "s1"

    shots: list[ShotPlan] = []
    for cs in contract.shots:
        decor = _field(by_dept, cs.id, "decor")
        shots.append(
            ShotPlan(
                id=cs.id,
                kind="photo" if cs.kind.strip().lower() == "photo" else "video",
                visual_desc=decor,
                motion_desc="static camera",
                narration_fr=_field(by_dept, cs.id, "narration"),
                duration_s=_clamp_duration(_field(by_dept, cs.id, "duration")),
                decor=decor,
                lighting=_field(by_dept, cs.id, "lighting"),
                framing=_field(by_dept, cs.id, "framing"),
                characters=casting.shot_characters.get(cs.id, []),
            )
        )

    scene = ScenePlan(
        id=sid,
        title=scene_brief.title,
        environment_desc=da.env.get("decor", "") or scene_brief.environment,
        lighting=da.env.get("lighting", ""),
        context_text=scene_brief.intention,
        shots=shots,
    )

    transcript = [contract_turn(contract), *draft_turns(drafts)]
    return RoomResult(scene=scene, new_characters=casting.new_characters, transcript=transcript)
