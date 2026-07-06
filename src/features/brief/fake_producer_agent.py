"""Producteur FAKE — déterministe, hors-ligne (dev + tests).

Ignore le réseau : dérive un Brief plausible de l'idée par heuristiques simples,
sans jamais écraser les champs déjà fournis dans `partial` (l'humain garde la
main). Sert de défaut offline et de golden (mirror `FakeDistributionAgent`).
"""

from __future__ import annotations

from .model import Brief

# Mots-clés → ton proposé (heuristique déterministe, volontairement simple).
_TON_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("horreur", "horror", "peur", "flippant", "creepy"), "sombre et angoissant"),
    (("drôle", "funny", "humour", "comique", "meme"), "léger et drôle"),
    (("émouvant", "triste", "touchant", "emotion"), "émouvant et sincère"),
    (("astuce", "conseil", "tuto", "how", "apprendre"), "clair et pédagogique"),
)


def _guess_ton(idea: str) -> str:
    low = idea.lower()
    for needles, ton in _TON_HINTS:
        if any(n in low for n in needles):
            return ton
    return "dynamique et captivant"


class FakeProducerAgent:
    """Implémente `ProducerAgent` sans appel réseau."""

    def draft_brief(self, *, idea: str, partial: Brief | None = None) -> Brief:
        base = (partial or Brief()).model_dump()
        pitch = idea.strip() or "une vidéo verticale"
        # On ne remplit un champ que s'il est vide dans `partial` (l'humain prime).
        proposed = {
            "objectif": f"Faire découvrir : {pitch[:120]}",
            "audience": "créateurs et curieux sur mobile (18-34)",
            "plateforme": "tiktok",
            "duree_s": 30.0,
            "budget_usd": 0.0,
            "ton": _guess_ton(idea),
            "langue": "fr",
            "notes": "",
        }
        merged = {**proposed, **{k: v for k, v in base.items() if _is_set(k, v)}}
        return Brief.model_validate(merged)


def _is_set(key: str, value: object) -> bool:
    """Un champ de `partial` est « décidé » (donc prioritaire) s'il est non vide."""
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    return value is not None
