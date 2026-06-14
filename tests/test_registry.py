"""Tests du registre de briques (palette) — métadonnées uniquement.

Pures : aucun réseau, aucun import lourd. Le module sous test ne tire que
stdlib + typing, donc il se charge tel quel dans l'environnement de test.
"""

import pytest

from src.features.compositing.registry import (
    CONTRACTS,
    REGISTRY,
    Brick,
    CapabilityContract,
    CapabilityField,
    bricks_by_kind,
    get_brick,
    get_contract,
    model_satisfies,
    validate_params,
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


# ---------------------------------------------------------------------------
# E2 — Contrats de capacité + modèles préférés
# ---------------------------------------------------------------------------

CONTRACT_KINDS = ("image", "video", "voice")


def test_contracts_cover_expected_kinds():
    """CONTRACTS expose exactement image / video / voice."""
    assert set(CONTRACTS.keys()) == set(CONTRACT_KINDS)


@pytest.mark.parametrize("kind", CONTRACT_KINDS)
def test_contract_is_well_formed(kind):
    """Chaque contrat : kind cohérent, 3 modèles préférés, champs requis présents."""
    contract = get_contract(kind)
    assert isinstance(contract, CapabilityContract)
    assert contract.kind == kind
    # Exactement 3 modèles préférés (low-cost / quality-price / premium).
    assert len(contract.preferred_models) == 3
    assert all(
        isinstance(m, str) and "/" in m for m in contract.preferred_models
    )
    # Au moins un champ requis, tous bien typés.
    assert all(isinstance(f, CapabilityField) for f in contract.fields)
    required = [f for f in contract.fields if f.required]
    assert required, f"{kind} devrait avoir au moins un champ requis"


def test_contract_required_fields_per_kind():
    """Les champs requis attendus sont présents par kind."""
    img_required = {f.name for f in get_contract("image").fields if f.required}
    assert {"prompt"} <= img_required

    vid_required = {f.name for f in get_contract("video").fields if f.required}
    assert {"prompt", "duration", "image"} <= vid_required

    voice_required = {
        f.name for f in get_contract("voice").fields if f.required
    }
    assert {"text", "voice_id"} <= voice_required


def test_validate_params_reports_missing_required():
    """Un champ requis absent est reporté ; un champ optionnel absent ne l'est pas."""
    missing = validate_params("video", {"prompt": "x"})
    # duration et image manquent ; les optionnels (audio, motion) n'apparaissent pas.
    assert set(missing) == {"duration", "image"}


def test_validate_params_alias_satisfies():
    """Un alias satisfait le champ : image_input couvre le champ image."""
    missing = validate_params(
        "video",
        {"prompt": "x", "duration": 5, "image_input": "u"},
    )
    assert missing == []


def test_validate_params_none_value_does_not_satisfy():
    """Une clé présente mais à None ne satisfait pas un champ requis."""
    missing = validate_params(
        "video",
        {"prompt": "x", "duration": 5, "image": None},
    )
    assert missing == ["image"]


def test_validate_params_all_present_is_valid():
    """Tous les requis présents → aucune erreur."""
    assert validate_params("voice", {"text": "bonjour", "voice_id": "v1"}) == []


def test_model_satisfies_true_with_names():
    """model_satisfies True quand les noms requis figurent dans les propriétés."""
    contract = get_contract("video")
    props = {"prompt", "duration", "image", "fps", "seed"}
    assert model_satisfies(contract, props) is True


def test_model_satisfies_true_with_aliases():
    """model_satisfies True quand seuls des alias des champs requis figurent."""
    contract = get_contract("video")
    props = {"prompt", "num_frames", "start_image"}
    assert model_satisfies(contract, props) is True


def test_model_satisfies_false_when_required_absent():
    """model_satisfies False dès qu'un champ requis (et tous ses alias) manque."""
    contract = get_contract("video")
    props = {"prompt", "duration"}  # ni image ni aucun de ses alias
    assert model_satisfies(contract, props) is False


def test_preferred_models_satisfy_their_contract():
    """Garde-fou interne : les schémas requis modélisés satisfont le contrat."""
    # Schémas d'entrée (clés OpenAPI) vérifiés via Replicate MCP.
    schemas = {
        "black-forest-labs/flux-schnell": {"prompt", "aspect_ratio"},
        "bytedance/seedream-4.5": {"prompt", "image_input", "size"},
        "google/imagen-4-ultra": {"prompt", "aspect_ratio"},
        "wan-video/wan-2.2-i2v-fast": {"prompt", "num_frames", "image"},
        "prunaai/p-video": {"prompt", "duration", "image", "audio"},
        "kwaivgi/kling-v2.5-turbo-pro": {"prompt", "duration", "image"},
        "minimax/speech-02-turbo": {"text", "voice_id"},
        "minimax/speech-2.8-turbo": {"text", "voice_id"},
        "minimax/speech-2.8-hd": {"text", "voice_id"},
    }
    for kind in CONTRACT_KINDS:
        contract = get_contract(kind)
        for ref in contract.preferred_models:
            assert model_satisfies(contract, schemas[ref]), (
                f"{ref} ne satisfait pas le contrat {kind}"
            )


def test_get_contract_unknown_raises_keyerror():
    """get_contract sur un kind inconnu lève KeyError avec un message utile."""
    with pytest.raises(KeyError) as exc:
        get_contract("nope")
    assert "nope" in str(exc.value)
