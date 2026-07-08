"""Réalisateur FAKE — déterministe, hors-ligne (dev + tests).

Sans réseau, il assemble une **intro CYOA** canonique à partir de la description :
établissement (eye-open + 2 plaques de nom) → chaque compagnon face caméra pour te
convaincre → le narrateur « choisis ton compagnon : A ou B » → écran countdown flou.
C'est l'intro de l'exemple, en dur mais DÉTERMINISTE — la vraie richesse vient de
l'agent OpenAI. Les deux noms sont extraits de la description (2 prénoms capitalisés),
sinon repli « Étienne » / « Marc ». N'utilise que des effets présents dans `effects`.
"""

from __future__ import annotations

import re

from .model import BeatPlan, FragmentPlan, NameplatePlan

# Prénoms candidats : mots capitalisés (accents FR compris), hors début de phrase courant.
_NAME = re.compile(r"\b([A-ZÉÈÀÂÎÔÛÇ][a-zàâäéèêëîïôöùûüç]{2,})\b")
_STOP = {"Choisis", "Deux", "Une", "Video", "Vidéo", "Intro", "Nuit", "POV"}


def _two_names(description: str) -> tuple[str, str]:
    seen: list[str] = []
    for m in _NAME.findall(description):
        if m not in _STOP and m not in seen:
            seen.append(m)
        if len(seen) == 2:
            break
    if len(seen) == 2:
        return seen[0], seen[1]
    return "Étienne", "Marc"


class FakeDirectorAgent:
    """Implémente `DirectorAgent` sans appel réseau (intro CYOA déterministe)."""

    def assemble(
        self, *, description: str, part: str = "intro",
        effects: list[str], language: str = "fr",
    ) -> FragmentPlan:
        a, b = _two_names(description)
        has = set(effects)
        eye = "montage.eye_open" in has
        timer = "montage.timer" in has
        beats = [
            BeatPlan(
                id=f"{part}_env", kind="photo", duree_s=1.5, eye_open=eye,
                sujet="two companions stand facing you in the dark, waiting to be chosen",
                nameplates=[NameplatePlan(text=a, side="left"),
                            NameplatePlan(text=b, side="right")],
            ),
            BeatPlan(
                id=f"{part}_a", kind="video", duree_s=3.0,
                sujet=f"first-person POV, {a} leans toward the camera, unsettling",
                narration_fr="Reste avec moi cette nuit. Tu ne le regretteras pas.",
                nameplates=[NameplatePlan(text=a, side="left")],
            ),
            BeatPlan(
                id=f"{part}_b", kind="video", duree_s=3.0,
                sujet=f"first-person POV, {b} reaches a hand toward you, pleading",
                narration_fr="Ne l'écoute pas. Viens avec moi, je te ferai sortir vivant.",
                nameplates=[NameplatePlan(text=b, side="right")],
            ),
            BeatPlan(
                id=f"{part}_choose", kind="photo", duree_s=2.0,
                sujet="two dark doorways side by side, one warm one cold",
                narration_fr=f"Choisis ton compagnon pour la nuit : {a} ou {b}.",
            ),
        ]
        if timer:
            beats.append(BeatPlan(
                id=f"{part}_timer", kind="photo", duree_s=2.1, countdown=True,
                sujet="choose your companion, tense final seconds",
            ))
        return FragmentPlan(part=part, beats=beats)
