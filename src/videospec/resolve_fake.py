"""FakeAssetResolver — résout un VideoSpec en fichiers FACTICES, hors-ligne.

Implémente le port `AssetResolver` sans aucun appel réseau ni génération IA :
chaque asset déclaré devient un petit fichier local déterministe (image unie,
vidéo de couleur, silence WAV), et chaque voix reçoit un transcript factice
(mots répartis uniformément sur la durée). C'est ce qui permet de prouver toute
la chaîne `prompt → MP4` dans la boucle de vérification (SPEC §6, critère N1)
sans dépenser un centime — le passage en réel n'est qu'un échange de resolver.

Imports lourds (moviepy/PIL) au niveau module : importé uniquement par le chemin
de rendu/tests, jamais par `videospec/__init__.py`.
"""

from __future__ import annotations

import os
import wave
from typing import Dict, List, Tuple

from moviepy import ColorClip
from PIL import Image

from .models import (
    FileAsset,
    ImageAsset,
    VideoAsset,
    VideoSpec,
    VoiceAsset,
)
from .ports import ResolvedAssets

_FRAMERATE = 22050


def _color_for(asset_id: str) -> Tuple[int, int, int]:
    """Couleur sombre déterministe dérivée de l'id (variété visuelle, ton horreur)."""
    n = abs(hash(asset_id))
    return (20 + n % 60, 10 + (n // 7) % 40, 15 + (n // 13) % 50)


def _fake_words(text: str, duration: float) -> Tuple[Dict[str, object], ...]:
    """Transcript factice : un mot par token, réparti uniformément sur la durée."""
    tokens = text.split()
    if not tokens:
        return ()
    per = duration / len(tokens)
    return tuple(
        {"text": tok, "start": i * per, "end": (i + 1) * per}
        for i, tok in enumerate(tokens)
    )


def _write_silence(path: str, seconds: float) -> None:
    nframes = int(seconds * _FRAMERATE)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_FRAMERATE)
        wf.writeframes(b"\x00\x00" * nframes)


class FakeAssetResolver:
    """Implémente `AssetResolver` avec des assets factices (tests / dev offline)."""

    def __init__(
        self,
        voice_seconds: float = 1.2,
        video_seconds: float = 1.0,
    ) -> None:
        self.voice_seconds = voice_seconds
        self.video_seconds = video_seconds

    def resolve(self, spec: VideoSpec, project_dir: str) -> ResolvedAssets:
        os.makedirs(project_dir, exist_ok=True)
        w, h, fps = spec.canvas.width, spec.canvas.height, spec.canvas.fps
        paths: Dict[str, str] = {}
        transcripts: Dict[str, Tuple[Dict[str, object], ...]] = {}

        for a in spec.assets:
            if isinstance(a, ImageAsset):
                p = os.path.join(project_dir, f"{a.id}.png")
                Image.new("RGB", (w, h), _color_for(a.id)).save(p)
                paths[a.id] = p
            elif isinstance(a, VideoAsset):
                p = os.path.join(project_dir, f"{a.id}.mp4")
                dur = min(a.duration, self.video_seconds)
                clip = ColorClip(size=(w, h), color=_color_for(a.id)).with_duration(dur)
                clip.write_videofile(p, fps=fps, codec="libx264", audio=False, logger=None)
                clip.close()
                paths[a.id] = p
            elif isinstance(a, VoiceAsset):
                p = os.path.join(project_dir, f"{a.id}.wav")
                _write_silence(p, self.voice_seconds)
                paths[a.id] = p
                transcripts[a.id] = _fake_words(a.text, self.voice_seconds)
            elif isinstance(a, FileAsset):
                # Fichier statique déjà sur disque (SFX) : on pointe dessus tel quel.
                paths[a.id] = a.path

        heads: Dict[str, Tuple[float, float]] = {
            "left": (0.3, 0.4),
            "right": (0.7, 0.4),
        }
        return ResolvedAssets(paths=paths, heads=heads, transcripts=transcripts)
