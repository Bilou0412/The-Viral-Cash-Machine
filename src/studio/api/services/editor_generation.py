"""Editor generation service (E5) — runs the generative bricks of a document.

Mirrors :class:`AssetGenerationService` but for the timeline editor:
  1. load the `EditorDocumentRow`, parse the `EditorDocument`,
  2. order the generative bricks so a brick that references another brick's
     output (a ``"{brick:<id>}"`` placeholder in its params) runs AFTER it,
  3. for each brick: compile the final prompt from the brick prompt + the global
     narrative context (and local overrides) via `compile_prompt`,
  4. resolve any ``"{brick:<id>}"`` placeholder to the referenced asset's URL
     (uploaded to Replicate if it is a local path),
  5. validate the params against the brick's capability contract,
  6. `provider.run_model(model_ref, params)[0]` → download immediately to the
     editor export dir → persist an `Asset` row (``editor_document_id`` set,
     ``beat == brick.id``) + a `GenerationJob` + a best-effort `CostEntry`,
  7. publish the same SSE event shapes as the asset service, keyed by ``doc_id``.

Provider + downloader are injected so tests run fully offline.
"""

from __future__ import annotations

import os
import re
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....editor._fields import field_value
from ....editor.context import compile_prompt
from ....editor.document import (
    ClipBrick,
    EditorDocument,
    GenerativeBrick,
    GenNode,
)
from ....features import storage
from ....features.assets.ports import AssetProvider
from ....features.assets.replicate_provider import ReplicateAssetProvider
from ....features.compositing.registry import validate_params
from ...db.repositories import (
    AssetRepo,
    CostRepo,
    EditorDocRepo,
    JobRepo,
    ProjectRepo,
)
from ..events import bus
from . import cost_actual, pricing
from .generation import Downloader, _default_downloader, _upload_to_replicate
from .paths import editor_dir

# A param value like "{brick:hero_image}" pulls the output of brick "hero_image".
_BRICK_REF = re.compile(r"^\{brick:([^}]+)\}$")

# Brick kind -> the param key that should receive the compiled prompt.
_PROMPT_KEY = {"image": "prompt", "video": "prompt", "voice": "text"}
# Brick kind -> the Asset.kind to persist.
_ASSET_KIND = {"image": "image", "video": "video", "voice": "audio"}
_EXT = {"image": "png", "video": "mp4", "voice": "mp3"}


def _ordered_generative_bricks(doc: EditorDocument) -> list[GenerativeBrick]:
    """Topo-order generative bricks so referenced bricks come first.

    A brick whose params contain ``"{brick:X}"`` depends on brick X. Falls back
    to document order on a cycle (best-effort; never raises).
    """
    gens = [b for b in doc.bricks if isinstance(b, GenerativeBrick)]
    by_id = {b.id: b for b in gens}

    def deps(brick: GenerativeBrick) -> list[str]:
        out: list[str] = []
        for value in brick.params.values():
            if isinstance(value, str):
                m = _BRICK_REF.match(value)
                if m and m.group(1) in by_id:
                    out.append(m.group(1))
        return out

    ordered: list[GenerativeBrick] = []
    placed: set[str] = set()
    remaining = list(gens)
    # Iterate up to len(gens) passes; on a stall, flush the rest in order.
    for _ in range(len(remaining) + 1):
        progress = False
        still: list[GenerativeBrick] = []
        for brick in remaining:
            if all(d in placed for d in deps(brick)):
                ordered.append(brick)
                placed.add(brick.id)
                progress = True
            else:
                still.append(brick)
        remaining = still
        if not remaining:
            break
        if not progress:  # cycle / missing dep — flush deterministically
            ordered.extend(remaining)
            break
    return ordered


def _resolve_media_value(value: str, token: str | None) -> str | None:
    """Résout une valeur d'input média en URL utilisable par Replicate.

    URL http(s) → telle quelle ; **photo uploadée** (ref de stockage) ou chemin
    local → poussée vers la Files API Replicate ; sinon ``None`` (valeur laissée
    telle quelle par l'appelant). C'est le chaînon qui rend l'upload fluide
    (download/upload automatiques).
    """
    if not value:
        return None
    if value.startswith(("http://", "https://")):
        return value
    if storage.exists(value):
        return _upload_to_replicate(storage.materialize(value), token)
    if os.path.exists(value):
        return _upload_to_replicate(value, token)
    return None


def _resolve_brick_refs(
    params: dict[str, Any], outputs: dict[str, str], token: str | None = None
) -> dict[str, Any]:
    """Replace ``"{brick:X}"`` values by the (Replicate-uploaded) URL of X, and
    resolve **uploaded photos** (storage refs / local paths) to Replicate URLs.

    ``outputs`` maps brick id -> a usable URL. If the prior output is a local
    path, it is uploaded to Replicate first (best-effort); a missing/unknown ref
    is left as-is so `validate_params` can flag it.
    """
    resolved: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            m = _BRICK_REF.match(value)
            if m:
                ref = m.group(1)
                src = outputs.get(ref)
                if src and os.path.exists(src):
                    uploaded = _upload_to_replicate(src, token)
                    resolved[key] = uploaded or src
                elif src:
                    resolved[key] = src
                else:
                    resolved[key] = value  # unresolved -> let validation catch it
                continue
            # Phase 3 : photo uploadée (ref de stockage) ou fichier local → URL.
            if storage.exists(value) or os.path.exists(value):
                media = _resolve_media_value(value, token)
                if media is not None:
                    resolved[key] = media
                    continue
        resolved[key] = value
    return resolved


class EditorGenerationService:
    """Runs the generative bricks of an editor document and persists results."""

    def __init__(
        self,
        engine: Engine,
        provider: AssetProvider | None = None,
        downloader: Downloader | None = None,
        replicate_token: str | None = None,
    ) -> None:
        self.engine = engine
        self.provider = provider or ReplicateAssetProvider(api_token=replicate_token)
        self.downloader = downloader or _default_downloader
        self.replicate_token = replicate_token

    # -- helpers ----------------------------------------------------------

    def _load(self, doc_id: int) -> tuple[EditorDocument, str]:
        """Return (parsed document, on-disk export dir) for a document id."""
        with Session(self.engine) as session:
            row = EditorDocRepo(session).get(doc_id)
            if row is None:
                raise ValueError(f"editor document {doc_id} not found")
            project = ProjectRepo(session).get(row.project_id)
            project_name = (
                project.name if project else f"project_{row.project_id}"
            )
            doc_json = row.doc_json
        doc = EditorDocument.model_validate_json(doc_json)
        out_dir = editor_dir(project_name, doc_id)
        os.makedirs(out_dir, exist_ok=True)
        return doc, out_dir

    def _final_params(
        self, doc: EditorDocument, brick: GenerativeBrick, outputs: dict[str, str]
    ) -> tuple[dict[str, Any], str]:
        """Compile the prompt + resolve brick refs. Returns (params, prompt)."""
        params = _resolve_brick_refs(dict(brick.params), outputs, self.replicate_token)
        key = _PROMPT_KEY[brick.type]
        base_prompt = str(params.get(key, "") or "")
        prompt = compile_prompt(
            base_prompt,
            doc.global_context,
            brick.context_overrides,
            include_story=(brick.type != "voice"),
        )
        params[key] = prompt
        return params, prompt

    # -- public API -------------------------------------------------------

    def generate_document(self, doc_id: int) -> None:
        """Generate a document's bricks (blocking; bg task).

        Dispatch : briques composites `ClipBrick` (image → motion → narration, R1b)
        et briques plates `GenerativeBrick` legacy. **Idempotent** : un nœud dont
        l'`Asset` (editor_document_id, beat) est déjà `ready` + fichier présent
        n'est ni régénéré ni repayé (cœur du « pas cher »).
        """
        doc, out_dir = self._load(doc_id)
        clips = [b for b in doc.bricks if isinstance(b, ClipBrick)]
        flats = _ordered_generative_bricks(doc)
        total = sum(_clip_node_count(c) for c in clips) + len(flats)
        bus.publish(doc_id, {"type": "generation_started", "total": total})

        done = self._existing_done(doc_id)
        outputs: dict[str, str] = {}
        index = 0
        for clip in clips:
            index = self._generate_clip(doc, doc_id, clip, out_dir, done, outputs, index)
        for brick in flats:
            self._generate_one(doc, doc_id, brick, out_dir, outputs, index)
            index += 1

        bus.publish(doc_id, {"type": "generation_done", "total": total})

    def regenerate_brick(self, doc_id: int, brick_id: str) -> None:
        """Regenerate a single brick of a document in place (force, no skip)."""
        doc, out_dir = self._load(doc_id)
        brick = next((b for b in doc.bricks if b.id == brick_id), None)
        if brick is None:
            raise ValueError(f"brick {brick_id!r} not found in document {doc_id}")
        if isinstance(brick, ClipBrick):
            # force : aucune table `done` → tous les nœuds du clip régénérés. On
            # fournit les sorties des AUTRES briques (photo d'env de la scène) pour
            # que la ref `{brick:<env>.image}` du plan se résolve.
            clip_outputs: dict[str, str] = {}
            with Session(self.engine) as session:
                for asset in AssetRepo(session).assets_by_document(doc_id):
                    if asset.local_path:
                        clip_outputs[asset.beat] = asset.local_path
            self._generate_clip(doc, doc_id, brick, out_dir, {}, clip_outputs, 0)
            return
        if not isinstance(brick, GenerativeBrick):
            raise ValueError(f"brick {brick_id!r} is not generative")
        # Reuse already-downloaded outputs of OTHER bricks for cross-brick refs.
        outputs: dict[str, str] = {}
        with Session(self.engine) as session:
            for asset in AssetRepo(session).assets_by_document(doc_id):
                if asset.local_path:
                    outputs[asset.beat] = asset.local_path
        self._generate_one(doc, doc_id, brick, out_dir, outputs, 0)

    # -- core -------------------------------------------------------------

    def _existing_done(self, doc_id: int) -> dict[str, str]:
        """beat -> chemin local des Assets déjà `ready` ET présents sur disque."""
        out: dict[str, str] = {}
        with Session(self.engine) as session:
            for a in AssetRepo(session).assets_by_document(doc_id):
                p = a.local_path
                if (
                    a.status == "ready"
                    and p
                    and os.path.exists(p)
                    and os.path.getsize(p) > 0
                ):
                    out[a.beat] = p
        return out

    def _node_params(
        self,
        doc: EditorDocument,
        clip: ClipBrick,
        node: Any,  # GenNode | AudioChild
        contract_kind: str,
        outputs: dict[str, str],
        overrides: dict[str, Any],
        prompt_fallback: str = "",
    ) -> tuple[dict[str, Any], str]:
        """Params COMPLETS d'un nœud composite : ses ``params`` bruts (tous les inputs
        du modèle saisis en revue) + refs résolues + prompt compilé + clés dérivées
        (``overrides`` : image auto-liée, durée…) qui l'emportent. Miroir du chemin
        legacy `_final_params`, pour ne plus jeter aucun input.
        """
        params = _resolve_brick_refs(dict(node.params), outputs, self.replicate_token)
        for key, value in overrides.items():
            if value not in (None, ""):
                params[key] = value
        prompt_key = _PROMPT_KEY[contract_kind]
        base = str(field_value(params, contract_kind, prompt_key) or "") or prompt_fallback
        prompt = compile_prompt(
            base,
            doc.global_context,
            clip.context_overrides,
            include_story=(contract_kind != "voice"),
        )
        params[prompt_key] = prompt
        return params, prompt

    def _resolve_image_input(self, value: str, refs: dict[str, str]) -> str | None:
        """Résout une image de départ : ``{brick:X}`` (sortie d'une autre brique,
        ex. la photo d'environnement d'une scène) OU une photo uploadée/URL."""
        m = _BRICK_REF.match(value)
        if m:
            src = refs.get(m.group(1))
            if not src:
                return None
            if os.path.exists(src):
                return _upload_to_replicate(src, self.replicate_token)
            return src
        return _resolve_media_value(value, self.replicate_token)

    def _generate_clip(
        self,
        doc: EditorDocument,
        doc_id: int,
        clip: ClipBrick,
        out_dir: str,
        done: dict[str, str],
        outputs: dict[str, str],
        index: int,
    ) -> int:
        """Exécute un `ClipBrick` : image (first-frame) → motion → enfants narration.

        Idempotent via `done` (beat déjà prêt = sauté). `outputs` accumule les URLs
        produites (partagé entre briques) → un plan peut animer la **photo
        d'environnement de sa scène** (`{brick:<env>.image}`). Renvoie l'index après
        les nœuds exécutés.
        """
        cid = clip.id
        refs = {**done, **outputs}  # résolution des refs inter-briques (scène)
        img_beat = f"{cid}.image"
        img_params, img_prompt = self._node_params(
            doc, clip, clip.image, "image", refs, {}
        )
        img_url = self._run_or_skip(
            doc_id, out_dir, done, index, beat=img_beat,
            contract_kind="image", asset_kind="image",
            model_ref=clip.image.model_ref, params=img_params, prompt=img_prompt,
        )
        stored_img = img_url or done.get(img_beat)
        if stored_img:
            outputs[img_beat] = stored_img
            refs[img_beat] = stored_img
        index += 1

        if clip.kind == "video":
            motion = clip.motion or GenNode()
            # Image de départ : ref inter-brique (photo d'environnement de la scène)
            # ou photo explicite (upload/URL) ; sinon auto-lien sur la photo du plan.
            explicit = field_value(motion.params, "video", "image")
            explicit_url = (
                self._resolve_image_input(str(explicit), refs) if explicit else None
            )
            image_input = (
                explicit_url
                or img_url
                or _url_for_local(done.get(img_beat), self.replicate_token)
            )
            duration = _as_float(
                field_value(motion.params, "video", "duration"),
                clip.placement.duration or pricing.BEAT_VIDEO_SECONDS,
            )
            mot_beat = f"{cid}.motion"
            if not image_input:
                self._fail_node(
                    doc_id, mot_beat, "video",
                    "image source manquante (la first-frame a échoué)", index,
                )
            else:
                mot_params, mot_prompt = self._node_params(
                    doc, clip, motion, "video", refs,
                    {"image": image_input, "duration": duration},
                    prompt_fallback=img_prompt,
                )
                mot_url = self._run_or_skip(
                    doc_id, out_dir, done, index, beat=mot_beat,
                    contract_kind="video", asset_kind="video",
                    model_ref=motion.model_ref, params=mot_params, prompt=mot_prompt,
                )
                stored_mot = mot_url or done.get(mot_beat)
                if stored_mot:
                    outputs[mot_beat] = stored_mot
            index += 1

        for child in clip.children:
            voice_id = field_value(child.params, "voice", "voice_id") or "Deep_Voice_Man"
            ch_params, ch_prompt = self._node_params(
                doc, clip, child, "voice", refs, {"voice_id": voice_id}
            )
            self._run_or_skip(
                doc_id, out_dir, done, index, beat=child.id,
                contract_kind="voice", asset_kind="audio",
                model_ref=child.model_ref, params=ch_params, prompt=ch_prompt,
            )
            index += 1
        return index

    def _run_or_skip(
        self,
        doc_id: int,
        out_dir: str,
        done: dict[str, str],
        index: int,
        *,
        beat: str,
        contract_kind: str,
        asset_kind: str,
        model_ref: str,
        params: dict[str, Any],
        prompt: str,
    ) -> str | None:
        """Saute le nœud si déjà `ready` (idempotence), sinon le génère."""
        if beat in done:
            bus.publish(
                doc_id,
                {"type": "asset_skipped", "beat": beat,
                 "local_path": done[beat], "index": index},
            )
            return None
        url, _local = self._run_node(
            doc_id, out_dir, beat=beat, contract_kind=contract_kind,
            asset_kind=asset_kind, model_ref=model_ref, params=params,
            prompt=prompt, index=index,
        )
        return url

    def _fail_node(
        self, doc_id: int, beat: str, asset_kind: str, error: str, index: int
    ) -> None:
        """Persiste un Asset en échec pour un nœud non exécutable (dépendance KO)."""
        with Session(self.engine) as session:
            asset = AssetRepo(session).create(
                episode_id=0, beat=beat, kind=asset_kind, prompt="",
                status="failed", editor_document_id=doc_id,
            )
            assert asset.id is not None
            bus.publish(
                doc_id,
                {"type": "asset_failed", "asset_id": asset.id,
                 "beat": beat, "error": error, "index": index},
            )

    def _generate_one(
        self,
        doc: EditorDocument,
        doc_id: int,
        brick: GenerativeBrick,
        out_dir: str,
        outputs: dict[str, str],
        index: int,
    ) -> None:
        """Brique PLATE legacy : un appel, un Asset (chaînage via outputs)."""
        params, prompt = self._final_params(doc, brick, outputs)
        _url, local = self._run_node(
            doc_id, out_dir, beat=brick.id, contract_kind=brick.type,
            asset_kind=_ASSET_KIND[brick.type], model_ref=brick.model_ref,
            params=params, prompt=prompt, index=index,
        )
        if local:
            outputs[brick.id] = local

    def _run_node(
        self,
        doc_id: int,
        out_dir: str,
        *,
        beat: str,
        contract_kind: str,
        asset_kind: str,
        model_ref: str,
        params: dict[str, Any],
        prompt: str,
        index: int,
    ) -> tuple[str | None, str | None]:
        """Génère UN nœud → Asset/Job/Cost/SSE. Renvoie (url distante, chemin local).

        `contract_kind` ∈ image/video/voice (validation + coût + extension) ;
        `asset_kind` = `Asset.kind` persistée (image/video/audio). L'url distante
        (sortie `run_model`) sert au chaînage i2v ; le local est téléchargé.
        """
        with Session(self.engine) as session:
            asset_repo = AssetRepo(session)
            job_repo = JobRepo(session)
            cost_repo = CostRepo(session)

            asset = asset_repo.create(
                episode_id=0,  # editor assets are not tied to an episode
                beat=beat, kind=asset_kind, prompt=prompt,
                status="generating", editor_document_id=doc_id,
            )
            assert asset.id is not None
            asset_id = asset.id
            bus.publish(
                doc_id,
                {"type": "asset_started", "asset_id": asset_id,
                 "beat": beat, "kind": asset_kind, "index": index},
            )

            missing = validate_params(contract_kind, params)
            if missing:
                error = (
                    f"champs requis manquants pour {beat!r} "
                    f"({contract_kind}): {', '.join(missing)}"
                )
                job = job_repo.create(asset_id, model_ref, status="running")
                assert job.id is not None
                job_repo.mark_failed(job.id, error)
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": error},
                )
                return None, None

            job = job_repo.create(asset_id, model_ref, status="running")
            assert job.id is not None
            job_id = job.id

            try:
                outs = self.provider.run_model(model_ref, params)
                url = outs[0] if outs else ""
            except Exception as exc:  # provider failure -> mark failed
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return None, None

            filename = f"{_safe(beat)}.{_EXT[contract_kind]}"
            try:
                local = self.downloader(url, out_dir, filename) if url else None
            except Exception as exc:
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return None, None

            asset_repo.set_local_path(asset_id, local or "")
            job_repo.mark_done(job_id)

            ac = cost_actual.actual_cost(
                model_ref,
                _best_effort_cost(model_ref, contract_kind, params),
                self.provider.last_run,
            )
            cost_repo.create(
                job_id, ac.line.model, ac.line.amount_usd,
                units=ac.line.units, unit_kind=ac.line.unit_kind,
                source=ac.source, predict_time_s=ac.predict_time_s,
            )
            bus.publish(
                doc_id,
                {"type": "asset_ready", "asset_id": asset_id,
                 "local_path": local, "amount_usd": ac.line.amount_usd,
                 "cost_source": ac.source},
            )
            return url, local


def _safe(brick_id: str) -> str:
    """Filesystem-safe stem from a brick id."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", brick_id)


def _clip_node_count(clip: ClipBrick) -> int:
    """Nombre de nœuds génératifs d'un clip : image (+ motion si vidéo) + enfants."""
    return 1 + (1 if clip.kind == "video" else 0) + len(clip.children)


def _url_for_local(path: str | None, token: str | None = None) -> str | None:
    """URL utilisable pour un fichier local (upload Replicate, repli sur le chemin)."""
    if path and os.path.exists(path):
        return _upload_to_replicate(path, token) or path
    return None


def _best_effort_cost(
    model_ref: str, kind: str, params: dict[str, Any]
) -> pricing.CostLine:
    """Best-effort cost line for an editor brick — never blocks.

    Uses the rate card by brick kind; an unknown kind records a zero-amount line
    with unit_kind "unknown" so the ledger stays consistent (never blocks).
    """
    if kind == "image":
        return pricing.image_cost(1)
    if kind == "video":
        duration = _as_float(params.get("duration"), pricing.BEAT_VIDEO_SECONDS)
        return pricing.video_cost(duration)
    if kind == "voice":
        text = str(params.get("text", "") or "")
        return pricing.voice_cost(len(text))
    return pricing.CostLine(model_ref, 0.0, "unknown", 0.0)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def regenerate_brick(
    engine: Engine,
    doc_id: int,
    brick_id: str,
    provider: AssetProvider | None = None,
    downloader: Downloader | None = None,
    replicate_token: str | None = None,
) -> None:
    """Module-level wrapper to schedule a single-brick regeneration."""
    EditorGenerationService(
        engine,
        provider=provider,
        downloader=downloader,
        replicate_token=replicate_token,
    ).regenerate_brick(doc_id, brick_id)
