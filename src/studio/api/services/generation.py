"""Asset generation service — image-first, local download, DB + cost tracking.

Executes a `plan_episode_assets` plan against an `AssetProvider` (real Replicate
or the FakeAssetProvider in tests). For every asset it:
  1. creates an Asset row (status pending),
  2. calls the provider (image -> then its motion video; audio standalone),
  3. downloads the output to exports/ IMMEDIATELY (never store the expiring URL),
  4. records a GenerationJob + CostEntry,
  5. publishes SSE progress events.

The provider and the downloader are injected so tests run fully offline with no
network and no real files.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....features.assets.ports import AssetProvider
from ....features.assets.replicate_provider import ReplicateAssetProvider
from ....features.scripting.adventure import AdventureScript
from ....features.scripting.themes import THEMES, get_theme
from ...db.repositories import AssetRepo, CostRepo, EpisodeRepo, JobRepo
from ..events import bus
from . import cost_actual, pricing
from .cost_actual import ActualCost
from .generation_plan import PlannedAsset, plan_episode_assets
from .paths import episode_dir

# Default voice ids (fallback if the cloned narrator profile is unavailable).
NARRATOR_VOICE_ID = "Deep_Voice_Man"
CHARACTER_VOICE_ID = "Deep_Voice_Man"


def _narrator_voice() -> tuple[str, str | None]:
    """(voice_id, model) of the cloned 'conteur' narrator from its profile.

    Reads assets/narrator_voice.json (the durable cloned voice_id + the model it
    was cloned with). Falls back to the default minimax voice if absent.
    """
    import json

    try:
        with open("assets/narrator_voice.json", encoding="utf-8") as fh:
            data = json.load(fh)
        vid = data.get("voice_id")
        if vid:
            model = data.get("tts_model")
            # Replicate exige un ref complet owner/name (ex. minimax/speech-02-hd).
            if model and "/" not in model:
                model = f"minimax/{model}"
            return vid, model
    except Exception:
        pass
    return NARRATOR_VOICE_ID, None

# Signature: (url, folder, filename) -> local path or None.
Downloader = Callable[[str, str, str], str | None]


def _default_downloader(url: str, folder: str, filename: str) -> str | None:
    # Routes through the storage backend: local (default — identical to the old
    # download_file) or R2 (uploads, returns an object key). See features/storage.
    from ....features import storage

    return storage.persist_from_url(url, folder, filename)


def _ext_for(kind: str) -> str:
    return {"image": "png", "video": "mp4", "audio": "mp3"}[kind]


def _filename(asset: PlannedAsset) -> str:
    """Stable on-disk filename for a planned asset (round + beat + kind)."""
    prefix = "epi" if asset.round_index is None else f"r{asset.round_index}"
    safe_beat = asset.beat.replace(".", "_")
    return f"{prefix}_{safe_beat}.{_ext_for(asset.kind)}"


# --- R3 : chaînage par la dernière frame ----------------------------------

# Quel plan précédent nourrit la frame d'un plan donné (continuité timeline).
_CHAIN_SRC = {
    "environment": "action",
    "character": "environment",
    "fatal": "character",
    "survival": "character",
}


def _chain_source(
    round_index: int | None, beat: str, last_frame_by_key: dict[tuple[int | None, str], str]
) -> str | None:
    """URL de la dernière frame du plan source (None si pas dispo)."""
    stub = beat[: -len(".frame")] if beat.endswith(".frame") else beat
    if stub == "action":  # le 1er plan d'un round suit la survie du round précédent
        if round_index and round_index > 0:
            return last_frame_by_key.get((round_index - 1, "survival"))
        return None
    src = _CHAIN_SRC.get(stub)
    return last_frame_by_key.get((round_index, src)) if src else None


def _upload_to_replicate(path: str, token: str | None) -> str | None:
    """Upload un fichier local vers la Files API Replicate → URL (best-effort).

    ``token`` = clé Replicate de l'utilisateur courant (B.2). None → pas d'upload.
    """
    import json as _json
    import urllib.request
    import uuid

    if not token:
        return None
    boundary = uuid.uuid4().hex
    with open(path, "rb") as fh:
        data = fh.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"content\"; "
        f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: image/png\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "https://api.replicate.com/v1/files",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return str(_json.load(r)["urls"]["get"])


def _last_frame_url(video_path: str, token: str | None) -> str | None:
    """Extrait la dernière frame d'une vidéo locale et l'upload (best-effort).

    Renvoie None sur toute erreur (ex. fichier factice en test) → pas de
    chaînage, on retombe sur la seule référence perso (R2).
    """
    try:
        if (
            not video_path
            or not os.path.exists(video_path)
            or os.path.getsize(video_path) < 1000  # ignore les fakes de test
        ):
            return None
        import subprocess

        png = video_path + ".lastframe.png"
        subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.2", "-i", video_path, "-frames:v", "1", png],
            check=True,
            capture_output=True,
        )
        return _upload_to_replicate(png, token)
    except Exception:
        return None


class AssetGenerationService:
    """Runs the image-first generation plan for an episode and persists results."""

    def __init__(
        self,
        engine: Engine,
        provider: AssetProvider | None = None,
        downloader: Downloader | None = None,
        replicate_token: str | None = None,
        openai_key: str | None = None,
    ) -> None:
        self.engine = engine
        # B.2 : le provider réel porte le token Replicate de l'utilisateur ;
        # en test, `provider` (fake) est injecté et le token est ignoré.
        self.provider = provider or ReplicateAssetProvider(api_token=replicate_token)
        self.downloader = downloader or _default_downloader
        self.replicate_token = replicate_token
        self.openai_key = openai_key

    def export_dir(self, project_name: str, episode_id: int) -> str:
        return episode_dir(project_name, episode_id)

    def generate_episode(
        self,
        episode_id: int,
        script: AdventureScript,
        side: str = "left",
        with_intro: bool = True,
    ) -> None:
        """Generate every asset of an episode (blocking; run in a background task).

        L'INTRO est générée ici (en fin de passe) pour qu'elle soit TOUJOURS
        présente au montage, quel que soit le chemin choisi côté UI (« Monter »
        OU « Produire ») — corrige le bug « pas d'intro dans la vidéo finale ».
        """
        with Session(self.engine) as session:
            episode = EpisodeRepo(session).get(episode_id)
            if episode is None:
                raise ValueError(f"episode {episode_id} not found")
            from ...db.repositories import ProjectRepo

            project = ProjectRepo(session).get(episode.project_id)
            project_name = project.name if project else f"project_{episode.project_id}"
            draft = episode.draft_mode
            theme_name = episode.theme

        # DA de l'épisode (cascade thème) ; repli sur « horror » si inconnu.
        theme = get_theme(theme_name) if theme_name in THEMES else get_theme()
        plan = plan_episode_assets(script, side, theme)  # type: ignore[arg-type]
        out_dir = self.export_dir(project_name, episode_id)
        os.makedirs(out_dir, exist_ok=True)

        # Image URLs are remembered within this run so a *.motion video can reuse
        # the *.frame image it was generated from (image-first).
        frame_url_by_beat: dict[str, str] = {}
        # R3 — dernière frame de chaque vidéo (par (round, stub)) : sert de base
        # à la frame du plan suivant pour la CONTINUITÉ visuelle (fil rouge).
        last_frame_by_key: dict[tuple[int | None, str], str] = {}

        # IDEMPOTENCE : ne JAMAIS regénérer (donc re-payer) un asset déjà prêt sur
        # disque. « Produire » après « Générer » ne relance plus toute la passe.
        done = self._existing_done(episode_id)
        todo = [p for p in plan if (p.round_index, p.beat) not in done]
        skipped = len(plan) - len(todo)
        if skipped:
            bus.publish(episode_id, {"type": "generation_skipped", "count": skipped})
        # Réamorce les URLs des frames déjà présentes dont une vidéo À FAIRE a
        # besoin (image-first) + la réf perso pour la cohérence i2i des images.
        self._preseed_frame_urls(todo, done, frame_url_by_beat)

        bus.publish(episode_id, {"type": "generation_started", "total": len(todo)})
        for index, planned in enumerate(todo):
            self._generate_one(
                episode_id, planned, out_dir, draft, frame_url_by_beat,
                last_frame_by_key, index,
            )

        # Intro — best-effort, TOUJOURS tentée en prod pour qu'elle soit présente
        # quel que soit le chemin de montage. Ignorée hors-ligne/en test (pas de
        # token Replicate) et jamais bloquante (le reste de l'épisode est déjà là).
        if (
            with_intro
            and self.replicate_token
            and not self._has_intro(episode_id)
        ):
            try:
                from .intro import generate_intro

                generate_intro(
                    self.engine,
                    episode_id,
                    replicate_token=self.replicate_token,
                    openai_key=self.openai_key,
                )
            except Exception:  # l'intro ne doit jamais faire échouer la génération
                pass

        with Session(self.engine) as session:
            EpisodeRepo(session).update_status(episode_id, "assets")
        bus.publish(episode_id, {"type": "generation_done", "total": len(plan)})

    def _has_intro(self, episode_id: int) -> bool:
        """True si un asset d'intro a déjà été enregistré pour cet épisode."""
        with Session(self.engine) as session:
            assets = AssetRepo(session).assets_by_episode(episode_id)
        return any(a.beat == "intro" for a in assets)

    def _existing_done(
        self, episode_id: int
    ) -> dict[tuple[int | None, str], str]:
        """{(round_index, beat): local_path} des assets DÉJÀ prêts sur disque.

        Sert à l'idempotence : un asset déjà généré et téléchargé n'est ni recréé
        ni repayé. On garde le DERNIER chemin valide par (round, beat).
        """
        out: dict[tuple[int | None, str], str] = {}
        with Session(self.engine) as session:
            assets = AssetRepo(session).assets_by_episode(episode_id)
        from ....features import storage

        for a in assets:
            if a.status == "ready" and a.local_path and storage.exists(a.local_path):
                out[(a.round_index, a.beat)] = a.local_path
        return out

    def _preseed_frame_urls(
        self,
        todo: list[PlannedAsset],
        done: dict[tuple[int | None, str], str],
        frame_url_by_beat: dict[str, str],
    ) -> None:
        """Amorce frame_url_by_beat depuis les fichiers déjà présents.

        Quand une VIDÉO à (re)faire a sa première frame déjà sur disque (sautée),
        on ré-uploade cette frame locale → URL, pour que l'image-to-video garde sa
        source. Idem pour la réf perso (image_input i2i) si des images sont à faire.
        Aucun upload quand il n'y a rien à faire (todo vide) → coût nul.
        """
        need_ref = any(
            p.kind == "image" and p.beat != "char_reference" for p in todo
        )
        ref_key = (None, "char_reference")
        if need_ref and ref_key in done and "char_reference" not in frame_url_by_beat:
            url = _upload_to_replicate(done[ref_key], self.replicate_token)
            if url:
                frame_url_by_beat["char_reference"] = url
        for p in todo:
            if p.kind != "video":
                continue
            frame_beat = p.beat.replace(".motion", ".frame")
            key = (p.round_index, frame_beat)
            if frame_beat not in frame_url_by_beat and key in done:
                url = _upload_to_replicate(done[key], self.replicate_token)
                if url:
                    frame_url_by_beat[frame_beat] = url

    def _generate_one(
        self,
        episode_id: int,
        planned: PlannedAsset,
        out_dir: str,
        draft: bool,
        frame_url_by_beat: dict[str, str],
        last_frame_by_key: dict[tuple[int | None, str], str],
        index: int,
    ) -> None:
        with Session(self.engine) as session:
            asset_repo = AssetRepo(session)
            job_repo = JobRepo(session)
            cost_repo = CostRepo(session)

            prompt = planned.motion_prompt or planned.image_prompt or planned.text
            asset = asset_repo.create(
                episode_id=episode_id,
                beat=planned.beat,
                kind=planned.kind,
                round_index=planned.round_index,
                prompt=prompt,
                draft=draft,
                status="generating",
            )
            assert asset.id is not None  # set by the DB on commit
            asset_id = asset.id
            bus.publish(
                episode_id,
                {
                    "type": "asset_started",
                    "asset_id": asset_id,
                    "beat": planned.beat,
                    "kind": planned.kind,
                    "index": index,
                },
            )

            model, url, ac = self._call_provider(
                planned, draft, frame_url_by_beat, last_frame_by_key
            )
            job = job_repo.create(asset_id, model, status="running")
            assert job.id is not None
            job_id = job.id

            try:
                local = self.downloader(url, out_dir, _filename(planned)) if url else None
            except Exception as exc:  # download failure -> mark job failed
                job_repo.mark_failed(job_id, str(exc))
                bus.publish(
                    episode_id,
                    {"type": "asset_failed", "asset_id": asset_id, "error": str(exc)},
                )
                return

            asset_repo.set_local_path(asset_id, local or "")
            # R3 — mémorise la dernière frame d'une vidéo pour chaîner la suivante.
            if planned.kind == "video" and local:
                lf = _last_frame_url(local, self.replicate_token)
                if lf:
                    stub = (
                        planned.beat[: -len(".motion")]
                        if planned.beat.endswith(".motion")
                        else planned.beat
                    )
                    last_frame_by_key[(planned.round_index, stub)] = lf
            job_repo.mark_done(job_id)
            cost_repo.create(
                job_id,
                ac.line.model,
                ac.line.amount_usd,
                units=ac.line.units,
                unit_kind=ac.line.unit_kind,
                source=ac.source,
                predict_time_s=ac.predict_time_s,
            )
            bus.publish(
                episode_id,
                {
                    "type": "asset_ready",
                    "asset_id": asset_id,
                    "local_path": local,
                    "amount_usd": ac.line.amount_usd,
                    "cost_source": ac.source,
                },
            )

    def _call_provider(
        self,
        planned: PlannedAsset,
        draft: bool,
        frame_url_by_beat: dict[str, str],
        last_frame_by_key: dict[tuple[int | None, str], str],
    ) -> tuple[str, str, ActualCost]:
        """Dispatch to the right provider; return (model, url, ACTUAL cost).

        The estimate line is the pre-flight rate-card; ``cost_actual`` upgrades it
        to the real cost from the provider's metered run (``provider.last_run``).
        """
        if planned.kind == "image":
            # image_input = réf perso (R2, cohérence) + dernière frame du plan
            # précédent (R3, continuité). La réf perso elle-même n'en a pas.
            refs: list[str] = []
            ref = frame_url_by_beat.get("char_reference")
            if ref and planned.beat != "char_reference":
                refs.append(ref)
            if planned.beat.endswith(".frame"):
                chain = _chain_source(
                    planned.round_index, planned.beat, last_frame_by_key
                )
                if chain:
                    refs.append(chain)
            url = self.provider.generate_image(
                planned.image_prompt or "", "2K", "9:16", image_input=(refs or None)
            )
            frame_url_by_beat[planned.beat] = url
            ac = cost_actual.actual_cost(
                pricing.MODEL_IMAGE, pricing.image_cost(1), self.provider.last_run
            )
            return pricing.MODEL_IMAGE, url, ac

        if planned.kind == "video":
            # Reuse the frame generated just before (image-first).
            frame_beat = planned.beat.replace(".motion", ".frame")
            image_url = frame_url_by_beat.get(frame_beat, "")
            url = self.provider.animate_video(
                planned.motion_prompt or "",
                image_url,
                duration=pricing.BEAT_VIDEO_SECONDS,
                aspect_ratio="9:16",
                resolution="720p",
                draft=draft,
            )
            ac = cost_actual.actual_cost(
                pricing.MODEL_VIDEO,
                pricing.video_cost(pricing.BEAT_VIDEO_SECONDS, draft=draft),
                self.provider.last_run,
            )
            return pricing.MODEL_VIDEO, url, ac

        # audio — narration beats use the cloned 'conteur' narrator voice.
        text = planned.text or ""
        if planned.beat.endswith("narration"):
            voice_id, model = _narrator_voice()
        else:
            voice_id, model = CHARACTER_VOICE_ID, None
        url = self.provider.synthesize_voice(text, voice_id, model)
        ac = cost_actual.actual_cost(
            pricing.MODEL_VOICE, pricing.voice_cost(len(text)), self.provider.last_run
        )
        return pricing.MODEL_VOICE, url, ac


def regenerate_asset(
    engine: Engine,
    asset_id: int,
    provider: AssetProvider | None = None,
    downloader: Downloader | None = None,
    replicate_token: str | None = None,
    openai_key: str | None = None,
) -> int | None:
    """Regenerate a single existing asset in place. Returns its episode id.

    Reuses the stored prompt. For a video asset it needs a source frame; if none
    is available it regenerates from an empty source (the provider handles it).
    """
    svc = AssetGenerationService(
        engine,
        provider=provider,
        downloader=downloader,
        replicate_token=replicate_token,
        openai_key=openai_key,
    )
    with Session(engine) as session:
        asset = AssetRepo(session).get(asset_id)
        if asset is None:
            return None
        episode = EpisodeRepo(session).get(asset.episode_id)
        from ...db.repositories import ProjectRepo

        project = (
            ProjectRepo(session).get(episode.project_id) if episode else None
        )
        project_name = project.name if project else "project"
        episode_id = asset.episode_id
        planned = PlannedAsset(
            round_index=asset.round_index,
            beat=asset.beat,
            kind=asset.kind,  # type: ignore[arg-type]
            image_prompt=asset.prompt if asset.kind != "audio" else None,
            motion_prompt=asset.prompt if asset.kind == "video" else None,
            text=asset.prompt if asset.kind == "audio" else None,
        )
        draft = episode.draft_mode if episode else True

    out_dir = svc.export_dir(project_name, episode_id)
    os.makedirs(out_dir, exist_ok=True)
    svc._generate_one(episode_id, planned, out_dir, draft, {}, {}, 0)
    return episode_id
