"""S1 — durcissement du chemin réel « Créer » (offline, sans clés).

Verrouille les invariants du rail scènes réel :
  - décrypteur OpenAI (client STUB, aucun réseau) : plan macro vide → erreur claire
    (`SceneDecompositionError`) plutôt qu'une vidéo vide ; scène sans shot → plan
    minimal synthétisé ;
  - génération (fake provider à URLs uniques) : chaque plan vidéo anime la photo
    d'ENVIRONNEMENT de sa scène (câblage cross-brick `{brick:<env>.image}`),
    idempotence (2ᵉ run = 0 appel), et robustesse à l'ORDRE (briques inversées →
    la ref se résout encore grâce au tri topologique des clips).
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("sqlmodel")

from sqlmodel import Session, create_engine

from src.features.assets.ports import RunResult
from src.features.scenes import scene_plan_to_document
from src.features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from src.features.scenes.openai_scene_decomposer import OpenAISceneDecomposer
from src.features.scenes.ports import SceneDecompositionError
from src.studio.api.services.editor_generation import EditorGenerationService
from src.studio.api.services.fakes import FakeAssetProvider
from src.studio.db.engine import init_db
from src.studio.db.repositories import AssetRepo, EditorDocRepo

# -- décrypteur OpenAI : client stub scripté (aucun réseau) -------------------

class _Msg:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _Completions:
    def __init__(self, scripted: list[str]) -> None:
        self._scripted = scripted
        self._i = 0

    def create(self, **_kw: object) -> _Resp:
        content = self._scripted[min(self._i, len(self._scripted) - 1)]
        self._i += 1
        return _Resp(content)


class _Chat:
    def __init__(self, scripted: list[str]) -> None:
        self.completions = _Completions(scripted)


class _StubClient:
    def __init__(self, scripted: list[str]) -> None:
        self.chat = _Chat(scripted)


def test_empty_macro_raises_scene_decomposition_error():
    """Macro illisible/vide → erreur claire, pas de VideoPlan vide silencieux."""
    dec = OpenAISceneDecomposer(_StubClient(['{"scenes": []}']), "gpt-x")
    with pytest.raises(SceneDecompositionError):
        dec.decompose_video("une idée", n_scenes=2)


def test_scene_without_shots_gets_a_minimal_plan():
    """Micro vide pour une scène → un plan minimal synthétisé (scène générable)."""
    macro = (
        '{"scenes":[{"id":"s1","title":"Intro","environment_desc":'
        '"a dark room","intention":"on entre"}]}'
    )
    dec = OpenAISceneDecomposer(_StubClient([macro, '{"shots": []}']), "gpt-x")
    plan = dec.decompose_video("thriller", n_scenes=1)
    assert len(plan.scenes) == 1
    shots = plan.scenes[0].shots
    assert len(shots) == 1
    assert shots[0].kind == "video"
    assert shots[0].visual_desc == "a dark room"  # anime la photo d'environnement


class _RaisingCompletions:
    def create(self, **_kw: object) -> Any:
        raise RuntimeError("401 invalid api key")


class _RaisingChat:
    def __init__(self) -> None:
        self.completions = _RaisingCompletions()


class _RaisingClient:
    """Client OpenAI qui lève à l'appel (clé invalide / modèle inconnu / quotas)."""

    def __init__(self) -> None:
        self.chat = _RaisingChat()


def test_openai_api_error_raises_scene_decomposition_error():
    """C-2 : une erreur API (clé/modèle/quotas) → `SceneDecompositionError` (→ 502
    lisible côté route), PAS un `ValueError` non mappé (→ 500 générique)."""
    dec = OpenAISceneDecomposer(_RaisingClient(), "gpt-x")
    with pytest.raises(SceneDecompositionError):
        dec.decompose_video("une idée", n_scenes=1)


# -- génération réelle : provider à URLs UNIQUES pour discriminer les frames --

class _UniqueProvider(FakeAssetProvider):
    """Comme `FakeAssetProvider` mais chaque appel renvoie une URL UNIQUE, pour
    distinguer la photo d'env de la photo propre d'un plan."""

    def run_model_metered(self, model_ref: str, params: dict[str, Any]) -> RunResult:
        self.run_calls.append((model_ref, params))
        self._n += 1
        url = f"https://fake.local/run/{self._n}.out"
        self.last_run = RunResult(
            urls=[url], predict_time=1.0, metrics={"predict_time": 1.0}
        )
        return self.last_run


def _fake_downloader(url: str, folder: str, filename: str) -> str:
    import os

    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(b"fake-bytes")
    return path


def _engine(tmp_path: Any):
    eng = create_engine(
        f"sqlite:///{tmp_path / 'realpath.db'}",
        connect_args={"check_same_thread": False},
    )
    init_db(eng)
    return eng


def _persist_scene_doc(engine: Any, *, reverse_bricks: bool = False) -> int:
    plan = FakeSceneDecomposer().decompose_video("x", n_scenes=1)
    doc = scene_plan_to_document(plan)
    if reverse_bricks:
        # Simule un doc réordonné (plan avant sa photo d'env) : le tri topologique
        # des clips doit quand même générer l'env en premier.
        doc = doc.model_copy(update={"bricks": list(reversed(doc.bricks))})
    with Session(engine) as s:
        row = EditorDocRepo(s).create(
            1, doc.title, doc.model_dump_json(), schema_version=doc.schema_version
        )
        assert row.id is not None
        return row.id


def _video_calls(provider: _UniqueProvider) -> list[dict[str, Any]]:
    return [params for model, params in provider.run_calls if model == "prunaai/p-video"]


def test_video_shots_animate_scene_env_photo(tmp_path):
    """Chaque plan vidéo reçoit comme `image` l'URL de la photo d'env (pas la sienne)."""
    engine = _engine(tmp_path)
    doc_id = _persist_scene_doc(engine)
    provider = _UniqueProvider()
    svc = EditorGenerationService(engine, provider=provider, downloader=_fake_downloader)
    svc.generate_document(doc_id)

    # 1re image générée = la photo d'ENV (clip photo, en tête après tri) → run/1.
    env_url = "https://fake.local/run/1.out"
    videos = _video_calls(provider)
    assert videos, "au moins un plan vidéo généré"
    for params in videos:
        assert params["image"] == env_url


def test_generation_is_idempotent(tmp_path):
    """2ᵉ run : tous les nœuds déjà prêts → 0 appel provider."""
    engine = _engine(tmp_path)
    doc_id = _persist_scene_doc(engine)
    provider = _UniqueProvider()
    svc = EditorGenerationService(engine, provider=provider, downloader=_fake_downloader)
    svc.generate_document(doc_id)
    first = len(provider.run_calls)
    assert first > 0
    svc.generate_document(doc_id)
    assert len(provider.run_calls) == first  # aucun nouvel appel

    with Session(engine) as s:
        assets = AssetRepo(s).assets_by_document(doc_id)
    assert all(a.status == "ready" for a in assets)


def test_env_ref_resolves_regardless_of_brick_order(tmp_path):
    """Doc réordonné (plan avant env) : le tri topologique résout quand même la ref."""
    engine = _engine(tmp_path)
    doc_id = _persist_scene_doc(engine, reverse_bricks=True)
    provider = _UniqueProvider()
    svc = EditorGenerationService(engine, provider=provider, downloader=_fake_downloader)
    svc.generate_document(doc_id)

    env_url = "https://fake.local/run/1.out"  # env toujours généré en premier
    videos = _video_calls(provider)
    assert videos
    for params in videos:
        assert params["image"] == env_url


# -- C-3 : propagation du mode draft (coût) sur le rail éditeur ----------------

def test_draft_mode_propagates_to_video_nodes(tmp_path):
    """`draft=True` → chaque nœud vidéo reçoit `draft=True` (qualité/coût brouillon)."""
    engine = _engine(tmp_path)
    doc_id = _persist_scene_doc(engine)
    provider = _UniqueProvider()
    svc = EditorGenerationService(
        engine, provider=provider, downloader=_fake_downloader, draft=True
    )
    svc.generate_document(doc_id)
    videos = _video_calls(provider)
    assert videos
    assert all(params.get("draft") is True for params in videos)


def test_default_is_not_draft(tmp_path):
    """Défaut (pas de draft) → `draft=False` sur les nœuds vidéo (pleine qualité)."""
    engine = _engine(tmp_path)
    doc_id = _persist_scene_doc(engine)
    provider = _UniqueProvider()
    svc = EditorGenerationService(engine, provider=provider, downloader=_fake_downloader)
    svc.generate_document(doc_id)
    assert all(params.get("draft") is False for params in _video_calls(provider))


# -- C-4 : garde-fou d'une ref {brick:} non résolue ---------------------------

def _persist_doc_with_dangling(engine: Any) -> int:
    """Doc dont la photo d'env porte une ref `{brick:ghost}` non résoluble."""
    from src.editor.document import EditorDocument

    plan = FakeSceneDecomposer().decompose_video("x", n_scenes=1)
    data = scene_plan_to_document(plan).model_dump()
    for b in data["bricks"]:
        if b.get("image"):
            b["image"]["params"]["ghost"] = "{brick:ghost}"
            break
    doc = EditorDocument.model_validate(data)
    with Session(engine) as s:
        row = EditorDocRepo(s).create(
            1, doc.title, doc.model_dump_json(), schema_version=doc.schema_version
        )
        assert row.id is not None
        return row.id


def test_unresolved_brick_ref_fails_without_calling_provider(tmp_path):
    """Une ref `{brick:…}` restée littérale → asset en échec, JAMAIS envoyée au provider."""
    engine = _engine(tmp_path)
    doc_id = _persist_doc_with_dangling(engine)
    provider = _UniqueProvider()
    svc = EditorGenerationService(engine, provider=provider, downloader=_fake_downloader)
    svc.generate_document(doc_id)

    # La valeur pendouillante n'a jamais atteint Replicate.
    assert not any("ghost" in str(params) for _model, params in provider.run_calls)
    with Session(engine) as s:
        assets = AssetRepo(s).assets_by_document(doc_id)
    assert any(a.status == "failed" for a in assets)


# -- préflight du harnais dogfood (C-1 : vérif des slugs, stub) ----------------

def test_preflight_check_models_flags_bad_slug():
    """`--check` : un slug absent (models.get lève) → ligne rouge ; bon slug → verte."""
    from scripts.dogfood_editor import check_models

    def models_get(slug: str) -> object:
        if slug == "bad/model":
            raise RuntimeError("404 Not Found")
        return {"slug": slug}

    rows = check_models(models_get, ("good/one", "bad/model"))
    assert rows[0].ok and rows[0].label.endswith("good/one")
    assert not rows[1].ok and "introuvable" in rows[1].detail
