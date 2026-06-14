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
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....editor.context import compile_prompt
from ....editor.document import EditorDocument, GenerativeBrick
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
from . import pricing
from .generation import Downloader, _default_downloader, _upload_to_replicate
from .paths import editor_dir

# A param value like "{brick:hero_image}" pulls the output of brick "hero_image".
_BRICK_REF = re.compile(r"^\{brick:([^}]+)\}$")

# Brick kind -> the param key that should receive the compiled prompt.
_PROMPT_KEY = {"image": "prompt", "video": "prompt", "voice": "text"}
# Brick kind -> the Asset.kind to persist.
_ASSET_KIND = {"image": "image", "video": "video", "voice": "audio"}
_EXT = {"image": "png", "video": "mp4", "voice": "mp3"}


def _ordered_generative_bricks(doc: EditorDocument) -> List[GenerativeBrick]:
    """Topo-order generative bricks so referenced bricks come first.

    A brick whose params contain ``"{brick:X}"`` depends on brick X. Falls back
    to document order on a cycle (best-effort; never raises).
    """
    gens = [b for b in doc.bricks if isinstance(b, GenerativeBrick)]
    by_id = {b.id: b for b in gens}

    def deps(brick: GenerativeBrick) -> List[str]:
        out: List[str] = []
        for value in brick.params.values():
            if isinstance(value, str):
                m = _BRICK_REF.match(value)
                if m and m.group(1) in by_id:
                    out.append(m.group(1))
        return out

    ordered: List[GenerativeBrick] = []
    placed: set[str] = set()
    remaining = list(gens)
    # Iterate up to len(gens) passes; on a stall, flush the rest in order.
    for _ in range(len(remaining) + 1):
        progress = False
        still: List[GenerativeBrick] = []
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


def _resolve_brick_refs(
    params: Dict[str, Any], outputs: Dict[str, str]
) -> Dict[str, Any]:
    """Replace ``"{brick:X}"`` values by the (Replicate-uploaded) URL of X.

    ``outputs`` maps brick id -> a usable URL. If the prior output is a local
    path, it is uploaded to Replicate first (best-effort); a missing/unknown ref
    is left as-is so `validate_params` can flag it.
    """
    resolved: Dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, str):
            m = _BRICK_REF.match(value)
            if m:
                ref = m.group(1)
                src = outputs.get(ref)
                if src and os.path.exists(src):
                    uploaded = _upload_to_replicate(src)
                    resolved[key] = uploaded or src
                elif src:
                    resolved[key] = src
                else:
                    resolved[key] = value  # unresolved -> let validation catch it
                continue
        resolved[key] = value
    return resolved


class EditorGenerationService:
    """Runs the generative bricks of an editor document and persists results."""

    def __init__(
        self,
        engine: Engine,
        provider: Optional[AssetProvider] = None,
        downloader: Optional[Downloader] = None,
    ) -> None:
        self.engine = engine
        self.provider = provider or ReplicateAssetProvider()
        self.downloader = downloader or _default_downloader

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
        self, doc: EditorDocument, brick: GenerativeBrick, outputs: Dict[str, str]
    ) -> tuple[Dict[str, Any], str]:
        """Compile the prompt + resolve brick refs. Returns (params, prompt)."""
        params = _resolve_brick_refs(dict(brick.params), outputs)
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
        """Generate every generative brick of a document (blocking; bg task)."""
        doc, out_dir = self._load(doc_id)
        bricks = _ordered_generative_bricks(doc)
        bus.publish(doc_id, {"type": "generation_started", "total": len(bricks)})

        # brick id -> local path of its downloaded output (for cross-brick refs).
        outputs: Dict[str, str] = {}
        for index, brick in enumerate(bricks):
            self._generate_one(doc, doc_id, brick, out_dir, outputs, index)

        bus.publish(doc_id, {"type": "generation_done", "total": len(bricks)})

    def regenerate_brick(self, doc_id: int, brick_id: str) -> None:
        """Regenerate a single brick of a document in place."""
        doc, out_dir = self._load(doc_id)
        brick = next(
            (
                b
                for b in doc.bricks
                if isinstance(b, GenerativeBrick) and b.id == brick_id
            ),
            None,
        )
        if brick is None:
            raise ValueError(
                f"generative brick {brick_id!r} not found in document {doc_id}"
            )
        # Reuse already-downloaded outputs of OTHER bricks for cross-brick refs.
        outputs: Dict[str, str] = {}
        with Session(self.engine) as session:
            for asset in AssetRepo(session).assets_by_document(doc_id):
                if asset.local_path:
                    outputs[asset.beat] = asset.local_path
        self._generate_one(doc, doc_id, brick, out_dir, outputs, 0)

    # -- core -------------------------------------------------------------

    def _generate_one(
        self,
        doc: EditorDocument,
        doc_id: int,
        brick: GenerativeBrick,
        out_dir: str,
        outputs: Dict[str, str],
        index: int,
    ) -> None:
        params, prompt = self._final_params(doc, brick, outputs)
        asset_kind = _ASSET_KIND[brick.type]

        with Session(self.engine) as session:
            asset_repo = AssetRepo(session)
            job_repo = JobRepo(session)
            cost_repo = CostRepo(session)

            asset = asset_repo.create(
                episode_id=0,  # editor assets are not tied to an episode
                beat=brick.id,
                kind=asset_kind,
                prompt=prompt,
                status="generating",
                editor_document_id=doc_id,
            )
            assert asset.id is not None
            asset_id = asset.id
            bus.publish(
                doc_id,
                {
                    "type": "asset_started",
                    "asset_id": asset_id,
                    "beat": brick.id,
                    "kind": asset_kind,
                    "index": index,
                },
            )

            # Validate required params (after prompt/ref resolution).
            missing = validate_params(brick.type, params)
            if missing:
                error = (
                    f"champs requis manquants pour la brique {brick.id!r} "
                    f"({brick.type}): {', '.join(missing)}"
                )
                job = job_repo.create(asset_id, brick.model_ref, status="running")
                assert job.id is not None
                job_repo.mark_failed(job.id, error)
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": error},
                )
                return

            job = job_repo.create(asset_id, brick.model_ref, status="running")
            assert job.id is not None
            job_id = job.id

            try:
                outs = self.provider.run_model(brick.model_ref, params)
                url = outs[0] if outs else ""
            except Exception as exc:  # provider failure -> mark failed
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return

            filename = f"{_safe(brick.id)}.{_EXT[brick.type]}"
            try:
                local = self.downloader(url, out_dir, filename) if url else None
            except Exception as exc:
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    doc_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return

            asset_repo.set_local_path(asset_id, local or "")
            if local:
                outputs[brick.id] = local
            job_repo.mark_done(job_id)

            cost_line = _best_effort_cost(brick.model_ref, brick.type, params)
            cost_repo.create(
                job_id,
                cost_line.model,
                cost_line.amount_usd,
                units=cost_line.units,
                unit_kind=cost_line.unit_kind,
            )
            bus.publish(
                doc_id,
                {
                    "type": "asset_ready",
                    "asset_id": asset_id,
                    "local_path": local,
                    "amount_usd": cost_line.amount_usd,
                },
            )


def _safe(brick_id: str) -> str:
    """Filesystem-safe stem from a brick id."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", brick_id)


def _best_effort_cost(
    model_ref: str, kind: str, params: Dict[str, Any]
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
    provider: Optional[AssetProvider] = None,
    downloader: Optional[Downloader] = None,
) -> None:
    """Module-level wrapper to schedule a single-brick regeneration."""
    EditorGenerationService(
        engine, provider=provider, downloader=downloader
    ).regenerate_brick(doc_id, brick_id)
