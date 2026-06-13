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
from moviepy.video.fx import MultiplySpeed, Resize

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
    # premières frames (images) des plans narrés — servent à PROLONGER le plan
    # quand la narration est plus longue que la vidéo (on n'illustre jamais du vide).
    action_frame: str = ""
    environment_frame: str = ""
    fatal_frame: str = ""
    survival_frame: str = ""


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


def _subs_cues(transcriber: Transcriber, audio_path: str) -> List[dict]:
    """Cues mot-à-mot (Whisper) bruts pour un audio."""
    if not audio_path or not os.path.exists(audio_path):
        return []
    return transcriber.transcribe(audio_path).to_list()


def _subs_from_audio(
    transcriber: Transcriber, audio_path: str, dur_cap: float
) -> List[ImageClip]:
    """Sous-titres mot-à-mot (Whisper) calés sur l'audio, à 78% de la hauteur."""
    cues = _subs_cues(transcriber, audio_path)
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


def _atempo(narr_path: str, factor: float, workdir: str) -> str:
    """Accélère un audio en préservant le pitch (ffmpeg atempo). Renvoie le chemin."""
    if factor <= 1.01:
        return narr_path
    import subprocess

    factor = min(2.0, factor)  # atempo : 0.5–2.0 en une passe
    out = os.path.join(workdir, "_at_" + os.path.basename(narr_path))
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", narr_path, "-filter:a", f"atempo={factor:.3f}", out],
            check=True, capture_output=True,
        )
        return out
    except Exception:
        return narr_path


def _narrated_video(
    video_path: str,
    frame_path: str,
    narr_path: str,
    transcriber: Transcriber,
    workdir: str = ".",
):
    """Plan vidéo narré : narration et vidéo CALÉES À LA MÊME DURÉE par la vitesse.

    cible = min(durée vidéo, durée narration). On accélère SEULEMENT le plus long
    jusqu'à la cible (l'autre reste à 1×) — jamais de ralenti ni d'allongement.
    Narrateur jamais coupé. Pas de plaque de nom (réservée à l'intro). Sous-titres.
    """
    v = VideoFileClip(video_path)
    t_vid = float(v.duration)
    narr0 = AudioFileClip(narr_path) if os.path.exists(narr_path) else None

    if narr0 is None:  # pas de narration : on garde la vidéo telle quelle
        base = _fit(v, t_vid)
        return base

    t_narr = float(narr0.duration)
    narr0.close()
    target = max(0.5, min(t_vid, t_narr))
    narr_atempo = t_narr / target   # >=1 si la narration est la plus longue
    vid_speed = t_vid / target      # >=1 si la vidéo est la plus longue

    vbase = _fit(v, t_vid)
    if vid_speed > 1.01:
        vbase = vbase.with_effects([MultiplySpeed(vid_speed)])
    seg = float(vbase.duration)
    safe = max(0.1, seg - 1.0 / FPS)

    narr_file = _atempo(narr_path, narr_atempo, workdir)
    narr = AudioFileClip(narr_file)

    tracks = []
    if vbase.audio is not None:
        tracks.append(_scale_volume(vbase.audio.with_duration(safe), 0.22))
    tracks.append(narr.with_duration(min(float(narr.duration), safe)))
    audio = CompositeAudioClip(tracks).with_duration(safe)

    # sous-titres calés sur la narration ACCÉLÉRÉE (timing correct)
    layers = [vbase] + _subs_from_audio(transcriber, narr_file, seg)
    comp = CompositeVideoClip(layers, size=(W, H)).with_duration(seg)
    return comp.with_audio(audio)


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
    layers = [base] + subs  # pas de plaque de nom (réservée à l'intro)
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
    ndur = float(narr.duration) if narr else 0.0
    total = max(4.0, ndur + 0.4)

    # Changement d'image AU BON MOMENT : à l'instant où le narrateur dit « ou »
    # (la bascule entre option A et option B). Sinon, au milieu.
    switch = total / 2
    cues = _subs_cues(transcriber, narr_path) if narr else []
    for c in cues:
        if c["text"].strip().lower().strip(".,!?") in ("ou", "or"):
            switch = max(0.6, min(total - 0.6, c["start"] + 0.1))
            break

    seq = concatenate_videoclips(
        [_ken_burns(a_img, switch), _ken_burns(b_img, total - switch)],
        method="compose",
    )
    subs = _subs_from_audio(transcriber, narr_path, total) if narr else []
    comp = CompositeVideoClip([seq, *subs], size=(W, H)).with_duration(total)
    if narr is not None:
        comp = comp.with_audio(narr.with_start(0.1))  # narration complète
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
    frame_path: str,
    narr_path: str,
    transcriber: Transcriber,
    output_path: str,
    workdir: Optional[str] = None,
) -> str:
    """Monte UN plan vidéo narré (ex. l'épilogue) en fichier autonome."""
    workdir = workdir or os.path.dirname(output_path) or "."
    os.makedirs(workdir, exist_ok=True)
    clip = _narrated_video(video_path, frame_path, narr_path, transcriber, workdir)
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
        _narrated_video(assets.action_video, assets.action_frame, assets.narr_action, transcriber, workdir),
        _narrated_video(assets.environment_video, assets.environment_frame, assets.narr_environment, transcriber, workdir),
        _facecam_video(assets.facecam_video, follower_name, transcriber, workdir),
        _choice_screen(assets.choice_a_image, assets.choice_b_image, assets.narr_choice, follower_name, transcriber),
        _timer_screen(assets.choice_b_image),
        _narrated_video(assets.fatal_video, assets.fatal_frame, assets.narr_fatal, transcriber, workdir),
        _narrated_video(assets.survival_video, assets.survival_frame, assets.narr_survival, transcriber, workdir),
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
