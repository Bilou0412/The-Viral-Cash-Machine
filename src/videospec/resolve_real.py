"""RealAssetResolver — résout un VideoSpec en VRAIS assets (Replicate + Whisper).

Implémente le port `AssetResolver` en réutilisant la machinerie existante :
  - `ReplicateAssetProvider` (seedream image, p-video i2v, minimax voix),
  - `download_file` (téléchargement IMMÉDIAT — les URLs Replicate expirent),
  - `WhisperTranscriber` (sous-titres mot-à-mot), `GroundingDINOHeadDetector`
    (positions de tête pour les nameplates).

C'est le jumeau réel de `FakeAssetResolver` : le moteur de rendu (`MoviePyRenderEngine`)
et toute la chaîne `produce()` sont identiques — seul le resolver change. Stratégie
de génération :
  1. l'image de RÉFÉRENCE personnage d'abord (sert d'`image_input` i2i à toutes
     les autres images → personnage + DA cohérents) ;
  2. les autres images, puis les voix ;
  3. les vidéos (image-to-video, à partir de l'URL fraîche de leur frame) ;
  4. transcripts (Whisper) des audios sous-titrés + détection de têtes.

Imports lourds en paresseux (dans __init__) : importer ce module reste léger.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .models import (
    FileAsset,
    ImageAsset,
    VideoAsset,
    VideoSpec,
    VoiceAsset,
)
from .ports import ResolvedAssets

if TYPE_CHECKING:
    from ..features.assets.ports import AssetProvider
    from ..features.compositing.heads import HeadDetector
    from ..features.transcription.ports import Transcriber


def _is_char_reference(asset_id: str) -> bool:
    return asset_id.endswith("char_reference")


class RealAssetResolver:
    """Implémente `AssetResolver` avec de vrais appels Replicate/OpenAI."""

    def __init__(
        self,
        provider: AssetProvider | None = None,
        transcriber: Transcriber | None = None,
        head_detector: HeadDetector | None = None,
        *,
        draft: bool = False,
        image_size: str = "2K",
        resolution: str = "720p",
        aspect_ratio: str = "9:16",
    ) -> None:
        if provider is None:
            from ..features.assets.replicate_provider import ReplicateAssetProvider

            provider = ReplicateAssetProvider()
        if transcriber is None:
            from ..features.transcription.whisper import WhisperTranscriber

            transcriber = WhisperTranscriber()
        if head_detector is None:
            from ..features.compositing.heads import GroundingDINOHeadDetector

            head_detector = GroundingDINOHeadDetector()
        self.provider = provider
        self.transcriber = transcriber
        self.head_detector = head_detector
        self.draft = draft
        self.image_size = image_size
        self.resolution = resolution
        self.aspect_ratio = aspect_ratio

    def resolve(self, spec: VideoSpec, project_dir: str) -> ResolvedAssets:
        from ..infra.download import download_file

        os.makedirs(project_dir, exist_ok=True)
        paths: dict[str, str] = {}
        urls: dict[str, str] = {}  # URL fraîche par id (chaînage image→vidéo)

        images = [a for a in spec.assets if isinstance(a, ImageAsset)]
        voices = [a for a in spec.assets if isinstance(a, VoiceAsset)]
        videos = [a for a in spec.assets if isinstance(a, VideoAsset)]
        files = [a for a in spec.assets if isinstance(a, FileAsset)]

        # 1) Image de référence personnage en premier (image_input i2i des autres).
        ref_url: str | None = None
        ref = next((a for a in images if _is_char_reference(a.id)), None)
        if ref is not None:
            print(f"[real] image (réf perso) {ref.id}…")
            ref_url = self.provider.generate_image(
                ref.prompt, self.image_size, ref.aspect_ratio
            )
            urls[ref.id] = ref_url
            self._dl(download_file, ref_url, project_dir, f"{ref.id}.png", paths, ref.id)

        # 2) Autres images (cohérence via image_input = réf perso).
        for img in images:
            if ref is not None and img.id == ref.id:
                continue
            print(f"[real] image {img.id}…")
            url = self.provider.generate_image(
                img.prompt,
                self.image_size,
                img.aspect_ratio,
                image_input=[ref_url] if ref_url else None,
            )
            urls[img.id] = url
            self._dl(download_file, url, project_dir, f"{img.id}.png", paths, img.id)

        # 3) Voix.
        for voice in voices:
            print(f"[real] voix {voice.id}…")
            url = self.provider.synthesize_voice(voice.text, voice.voice_id)
            urls[voice.id] = url
            self._dl(download_file, url, project_dir, f"{voice.id}.mp3", paths, voice.id)

        # 4) Vidéos (image-to-video à partir de l'URL fraîche de leur frame).
        for vid in videos:
            image_url = urls.get(vid.image)
            if not image_url:
                print(f"[real] ⚠ vidéo {vid.id} : frame {vid.image} absente, ignorée")
                continue
            audio_url = urls.get(vid.audio) if vid.audio else None
            print(f"[real] vidéo {vid.id} (i2v)…")
            url = self.provider.animate_video(
                vid.prompt,
                image_url,
                duration=vid.duration,
                aspect_ratio=self.aspect_ratio,
                resolution=self.resolution,
                audio_url=audio_url,
                draft=self.draft,
            )
            urls[vid.id] = url
            self._dl(download_file, url, project_dir, f"{vid.id}.mp4", paths, vid.id)

        # 5) Fichiers statiques (SFX) — déjà sur disque.
        for fa in files:
            paths[fa.id] = fa.path

        # 6) Transcripts (Whisper) des sources de sous-titres.
        transcripts: dict[str, tuple[dict[str, object], ...]] = {}
        for src in self._subtitle_sources(spec):
            local = paths.get(src)
            if local and os.path.exists(local):
                print(f"[real] transcription {src}…")
                cues = self.transcriber.transcribe(local).to_list()
                transcripts[src] = tuple(cues)

        # 7) Détection des têtes sur la réf perso (pour les nameplates).
        heads: dict[str, tuple[float, float]] = {"left": (0.3, 0.4), "right": (0.7, 0.4)}
        if ref is not None and paths.get(ref.id) and os.path.exists(paths[ref.id]):
            try:
                print("[real] détection des têtes…")
                layout = self.head_detector.detect(paths[ref.id], project_dir)
                heads = {"left": layout.left, "right": layout.right}
            except Exception as e:  # pragma: no cover - best effort
                print(f"[real] ⚠ détection têtes échouée ({e}), défauts utilisés")

        return ResolvedAssets(paths=paths, heads=heads, transcripts=transcripts)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _dl(download_file, url, folder, filename, paths, asset_id) -> None:  # type: ignore[no-untyped-def]
        local = download_file(url, folder, filename)
        if local:
            paths[asset_id] = local
        else:
            print(f"[real] ⚠ téléchargement échoué : {asset_id}")

    @staticmethod
    def _subtitle_sources(spec: VideoSpec) -> list[str]:
        out: list[str] = []
        for seg in spec.segments:
            subs = getattr(seg, "subtitles", None)
            src = getattr(subs, "source", None)
            if isinstance(src, str) and src not in out:
                out.append(src)
        return out
