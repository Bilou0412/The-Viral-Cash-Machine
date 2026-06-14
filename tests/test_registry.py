"""Tests du registre de briques (palette) — métadonnées uniquement.

Pures : aucun réseau, aucun import lourd. Le module sous test ne tire que
stdlib + typing, donc il se charge tel quel dans l'environnement de test.
"""

import pytest

from src.features.compositing.registry import (
    REGISTRY,
    Brick,
    bricks_by_kind,
    get_brick,
)

# Liste explicite des briques attendues : le garde-fou qui maintient la
# palette explicite. Toute brique ajoutée/retirée doit être reflétée ici.
EXPECTED_NAMES = {
    "image.seedream",
    "video.pvideo",
    "voice.minimax",
    "montage.timer",
    "montage.choice",
    "montage.subtitles",
    "montage.nameplate",
    "montage.zoom",
    "montage.facecam",
    "montage.narrate",
    "montage.eye_open",
}

KINDS = ("image", "video", "voice", "montage")


def test_registry_matches_expected_names():
    """Le registre contient EXACTEMENT les briques attendues."""
    assert set(REGISTRY.keys()) == EXPECTED_NAMES


@pytest.mark.parametrize("name", sorted(EXPECTED_NAMES))
def test_each_brick_resolves_and_is_well_formed(name):
    """Chaque nom résout via get_brick, avec summary et ref non vides."""
    brick = get_brick(name)
    assert isinstance(brick, Brick)
    assert brick.name == name
    assert brick.kind in KINDS
    assert brick.summary.strip(), f"summary vide pour {name}"
    assert brick.ref.strip(), f"ref vide pour {name}"
    # ref est une chaîne pointée, pas un import
    assert "." in brick.ref


def test_bricks_by_kind_partitions_registry():
    """Les catégories partitionnent le registre : pas de chevauchement, couverture totale."""
    collected: list[Brick] = []
    seen_names: set[str] = set()
    for kind in KINDS:
        group = bricks_by_kind(kind)
        for b in group:
            assert b.kind == kind
            assert b.name not in seen_names, f"chevauchement sur {b.name}"
            seen_names.add(b.name)
        collected.extend(group)
    assert seen_names == set(REGISTRY.keys())
    assert len(collected) == len(REGISTRY)


def test_bricks_by_kind_counts():
    """Répartition par catégorie : 1 image, 1 video, 1 voice, le reste montage."""
    assert len(bricks_by_kind("image")) == 1
    assert len(bricks_by_kind("video")) == 1
    assert len(bricks_by_kind("voice")) == 1
    assert len(bricks_by_kind("montage")) == len(REGISTRY) - 3


def test_bricks_by_kind_unknown_is_empty():
    """Une catégorie inconnue renvoie une liste vide."""
    assert bricks_by_kind("nope") == []


def test_get_brick_unknown_raises_keyerror():
    """get_brick sur un nom inconnu lève KeyError avec un message utile."""
    with pytest.raises(KeyError) as exc:
        get_brick("nope")
    assert "nope" in str(exc.value)
