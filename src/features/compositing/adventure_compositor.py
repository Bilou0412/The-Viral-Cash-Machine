"""Compositeur Aventure (MoviePy) — montage qualité d'un round/épisode.

Réutilise les briques existantes (SubtitleOverlay, TimerOverlay, GaugeOverlay,
NameplateOverlay) pour assembler la timeline POV avec :
- plaque de nom du perso suivi (haut de cadre),
- sous-titres mot-à-mot (Whisper) sur narration + face-cam,
- compte à rebours 3-2-1 + jauge + ticks à l'écran des choix,
- narration conteur mixée par-dessus l'ambiance, voix native sur le face-cam.

Entrée : chemins d'assets déjà générés (image-first) + textes du script.
Sortie : un fichier vidéo monté.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from PIL import Image, ImageFilter
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import Resize

from ..transcription.ports import Transcriber
from .overlays import GaugeOverlay, NameplateOverlay, SubtitleOverlay, TimerOverlay

W, H, FPS = 720, 1280, 24
TICK = os.path.join("assets", "tick.wav")
BEEP = os.path.join("assets", "final.wav")


def _scale_volume(audio, factor: float):
    """Baisse le volume d'un AudioClip (API MoviePy 2.x robuste)."""
    if hasattr(audio, "with_volume_scaled"):
        return audio.with_volume_scaled(factor)
    try:
        from moviepy.audio.fx import MultiplyVolume
        return audio.with_effects([MultiplyVolume(factor)])
    except Exception:
        return audio


@dataclass
class RoundAssets:
    """Chemins locaux des assets d'un round (image-first déjà généré)."""

    action_video: str
    environment_video: str
    facecam_video: str
    choice_a_image: str
    choice_b_image: str
    fatal_video: str
    survival_video: str
    # audios narrateur (conteur) déjà synthétisés
    narr_action: str
    narr_environment: str
    narr_choice: str
    narr_fatal: str
    narr_survival: str


def _ascii_upper(name: str) -> str:
    """Majuscules sans accents (la police Minecraft.ttf n'a pas les accentués)."""
    import unicodedata

    folded = unicodedata.normalize("NFKD", name)
    return "".join(c for c in folded if not unicodedata.combining(c)).upper()


def _nameplate(name: str, dur: float) -> ImageClip:
    """Plaque de nom du perso suivi, en haut de cadre."""
    plate = NameplateOverlay(
        text=_ascii_upper(name), fontsize=46, color="white", duration=dur, stroke_width=4
    ).to_clip((W, H))
    return plate.with_position(("center", 60))


def _subs_from_audio(
    transcriber: Transcriber, audio_path: str, dur_cap: float
) -> List[ImageClip]:
    """Sous-titres mot-à-mot (Whisper) calés sur l'audio, à 78% de la hauteur."""
    if not os.path.exists(audio_path):
        return []
    cues = transcriber.transcribe(audio_path).to_list()
    subs: List[ImageClip] = []
    for c in cues:
        if c["start"] >= dur_cap:
            continue
        end = min(c["end"], dur_cap)
        d = max(0.05, end - c["start"])
        badge = SubtitleOverlay(
            text=c["text"].upper(), fontsize=66, duration=d
        ).to_clip((W, H))
        subs.append(badge.with_start(c["start"]).with_position(("center", 0.78 * H)))
    return subs


def _fit(clip, dur: float):
    """Recadre/redimensionne un clip vidéo en 720x1280 et fixe la durée."""
    clip = clip.resized(height=H) if clip.h != H else clip
    if clip.w != W:
        clip = clip.with_effects([Resize((W, H))])
    return clip.with_duration(dur)


def _narrated_video(
    video_path: str, narr_path: str, name: str, transcriber: Transcriber
):
    """Plan vidéo narré : clip + nameplate + narration mixée + sous-titres."""
    v = VideoFileClip(video_path)
    # Durée = celle du clip (on n'étend pas : lire l'audio au-delà de sa fin
    # casse MoviePy). La narration courte rentre dedans ; on la borne par sûreté.
    dur = float(v.duration)
    safe = max(0.1, dur - 1.0 / FPS)  # marge anti-erreur de bord
    base = _fit(v, dur)

    narr = AudioFileClip(narr_path) if os.path.exists(narr_path) else None
    tracks = []
    if base.audio is not None:
        amb = _scale_volume(base.audio.with_duration(safe), 0.22)
        tracks.append(amb)
    if narr is not None:
        n = narr.with_duration(min(narr.duration, safe - 0.2)).with_start(0.2)
        tracks.append(n)
    audio = CompositeAudioClip(tracks).with_duration(safe) if tracks else None

    layers = [base, _nameplate(name, dur)]
    layers += _subs_from_audio(transcriber, narr_path, dur)
    comp = CompositeVideoClip(layers, size=(W, H)).with_duration(dur)
    return comp.with_audio(audio) if audio else comp


def _facecam_video(video_path: str, name: str, transcriber: Transcriber, workdir: str):
    """Face-cam : voix native conservée + nameplate + sous-titres de la voix native."""
    v = VideoFileClip(video_path)
    dur = float(v.duration)
    safe = max(0.1, dur - 1.0 / FPS)
    base = _fit(v, dur)
    # sous-titres : transcrire l'audio natif (extrait en wav)
    subs: List[ImageClip] = []
    native = base.audio
    if native is not None:
        wav = os.path.join(workdir, "_facecam_audio.wav")
        native.write_audiofile(wav, logger=None)
        subs = _subs_from_audio(transcriber, wav, dur)
    layers = [base, _nameplate(name, dur)] + subs
    comp = CompositeVideoClip(layers, size=(W, H)).with_duration(dur)
    return comp.with_audio(native.with_duration(safe)) if native is not None else comp


def _ken_burns(image_path: str, dur: float):
    """Image fixe avec zoom Ken Burns."""
    img = Image.open(image_path).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    clip = ImageClip(np.array(img)).with_duration(dur)
    clip = clip.with_effects([Resize(lambda t: 1.0 + 0.12 * (t / dur))])
    return clip.with_position("center")


def _choice_screen(
    a_img: str, b_img: str, narr_path: str, name: str, transcriber: Transcriber
):
    """Écran des choix : 2 photos qui se succèdent (Ken Burns) + narration + subs."""
    narr = AudioFileClip(narr_path) if os.path.exists(narr_path) else None
    total = max(5.0, (narr.duration + 0.4) if narr else 5.0)
    half = total / 2
    # les deux options se succèdent (Ken Burns), une moitié chacune
    seq = concatenate_videoclips(
        [_ken_burns(a_img, half), _ken_burns(b_img, half)], method="compose"
    )
    subs = _subs_from_audio(transcriber, narr_path, total) if narr else []
    comp = CompositeVideoClip([seq, _nameplate(name, total), *subs], size=(W, H)).with_duration(total)
    if narr is not None:
        comp = comp.with_audio(narr.with_start(0.2))
    return comp


def _timer_screen(bg_image: str):
    """Compte à rebours 3-2-1 sur fond flouté + jauge + ticks/beep."""
    T_STEP = 0.8
    dur = T_STEP * 3
    if os.path.exists(bg_image):
        img = Image.open(bg_image).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(radius=22))
        bg = ImageClip(np.array(img)).with_duration(dur)
    else:
        bg = ColorClip(size=(W, H), color=(20, 10, 10)).with_duration(dur)

    counts = [
        TimerOverlay(label=str(n), fontsize=170, size=240, duration=T_STEP)
        .to_clip((W, H))
        .with_start(i * T_STEP)
        .with_position(("center", "center"))
        for i, n in enumerate(["3", "2", "1"])
    ]
    gauge = GaugeOverlay(width=W, duration=dur).to_clip((W, H)).with_position(("center", int(0.66 * H)))

    audio_el = []
    if os.path.exists(TICK):
        for step in [0, T_STEP, 2 * T_STEP]:
            audio_el.append(AudioFileClip(TICK).with_start(step))
    if os.path.exists(BEEP):
        audio_el.append(AudioFileClip(BEEP).with_start(dur - 0.05))
    comp = CompositeVideoClip([bg, gauge, *counts], size=(W, H)).with_duration(dur)
    if audio_el:
        comp = comp.with_audio(CompositeAudioClip(audio_el))
    return comp


def compose_narrated_segment(
    video_path: str,
    narr_path: str,
    follower_name: str,
    transcriber: Transcriber,
    output_path: str,
    workdir: Optional[str] = None,
) -> str:
    """Monte UN plan vidéo narré (ex. l'épilogue) en fichier autonome."""
    workdir = workdir or os.path.dirname(output_path) or "."
    os.makedirs(workdir, exist_ok=True)
    clip = _narrated_video(video_path, narr_path, follower_name, transcriber)
    clip.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        temp_audiofile=os.path.join(workdir, "_temp_epi.m4a"), remove_temp=True,
        logger=None,
    )
    clip.close()
    return output_path


def compose_round(
    assets: RoundAssets,
    follower_name: str,
    transcriber: Transcriber,
    output_path: str,
    workdir: Optional[str] = None,
) -> str:
    """Assemble un round complet en MoviePy et écrit le fichier."""
    workdir = workdir or os.path.dirname(output_path) or "."
    os.makedirs(workdir, exist_ok=True)
    segments = [
        _narrated_video(assets.action_video, assets.narr_action, follower_name, transcriber),
        _narrated_video(assets.environment_video, assets.narr_environment, follower_name, transcriber),
        _facecam_video(assets.facecam_video, follower_name, transcriber, workdir),
        _choice_screen(assets.choice_a_image, assets.choice_b_image, assets.narr_choice, follower_name, transcriber),
        _timer_screen(assets.choice_b_image),
        _narrated_video(assets.fatal_video, assets.narr_fatal, follower_name, transcriber),
        _narrated_video(assets.survival_video, assets.narr_survival, follower_name, transcriber),
    ]
    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(
        output_path, fps=FPS, codec="libx264", audio_codec="aac",
        temp_audiofile=os.path.join(workdir, "_temp_audio.m4a"), remove_temp=True,
        logger=None,
    )
    dur = float(final.duration)
    final.close()
    return output_path
