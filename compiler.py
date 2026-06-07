import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, CompositeAudioClip
)


def create_text_clip_pil(
    text, fontsize, color, size,
    font_path="C:\\Windows\\Fonts\\arial.ttf",
    bg_color=(0, 0, 0, 0),
    duration=5,
    stroke_width=2,
    stroke_color="black"
):
    """Crée un clip texte via PIL quand ImageMagick est indisponible."""
    img = Image.new("RGBA", size, bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(font_path, fontsize)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((size[0] - tw) / 2, (size[1] - th) / 2)

    if stroke_width > 0:
        offsets = [
            (stroke_width, stroke_width), (stroke_width, -stroke_width),
            (-stroke_width, stroke_width), (-stroke_width, -stroke_width),
        ]
        for dx, dy in offsets:
            draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=stroke_color)

    draw.text(pos, text, font=font, fill=color)
    return ImageClip(np.array(img)).with_duration(duration)


def _make_text_clip(text, fsize, color, box_size, duration, stroke_w=3):
    """Essaie TextClip (MoviePy/ImageMagick), retombe sur PIL en cas d'échec."""
    try:
        return (
            TextClip(
                text=text, font_size=fsize, color=color,
                size=box_size, font="Arial",
                stroke_color="black", stroke_width=stroke_w,
            ).with_duration(duration)
        )
    except Exception:
        return create_text_clip_pil(text, fsize, color, box_size, duration=duration, stroke_width=stroke_w)


def compile_video(project_name: str, instance_id: str) -> str:
    """
    Compile les assets d'un projet en une vidéo finale avec mise au format automatique.
    """
    project_dir = os.path.join("exports", project_name, instance_id)
    paths = {
        "video":    os.path.join(project_dir, "video.mp4"),
        "image":    os.path.join(project_dir, "base_image.png"),
        "narrator": os.path.join(project_dir, "narrator.mp3"),
        "metadata": os.path.join(project_dir, "metadata.json"),
        "output":   os.path.join(project_dir, "final_video.mp4"),
        "tick":     os.path.join("assets", "tick.wav"),
        "beep":     os.path.join("assets", "final.wav"),
    }

    # Validation
    for key in ("video", "metadata"):
        if not os.path.exists(paths[key]):
            raise FileNotFoundError(f"Fichier requis manquant : {paths[key]}")

    with open(paths["metadata"], "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Nettoyage des noms
    def clean_name(raw: str, fallback: str) -> str:
        if not raw: return fallback
        for p in ["Monster A", "Monster L", "Monster B", "Monster R"]:
            raw = raw.replace(p, fallback)
        return raw

    name_l = clean_name(meta.get("char_left_name", ""), "Pierre")
    name_r = clean_name(meta.get("char_right_name", ""), "Jacques")
    speech  = meta.get("character_speech", "")
    choice_a = meta.get("choice_a", name_l)
    choice_b = meta.get("choice_b", name_r)

    video_clip = VideoFileClip(paths["video"])
    narrator_audio = None

    try:
        w, h = video_clip.size

        # --- PREPARATION DE L'IMAGE (MISE AU FORMAT) ---
        if os.path.exists(paths["image"]):
            # Forcer l'image au même format que la vidéo
            img_pil = Image.open(paths["image"]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
            base_image_clip = ImageClip(np.array(img_pil))
        else:
            base_image_clip = ColorClip(size=(w, h), color=(50, 50, 50))

        # ── PHASE 1 : Ouverture yeux sur image statique (2.0s) ──────────────────
        INTRO_DURATION = 2.0
        EYE_DURATION   = 0.8

        bar_top = (
            ColorClip(size=(w, h // 2), color=(0, 0, 0))
            .with_duration(EYE_DURATION)
            .with_position(lambda t: ("center", -(t / EYE_DURATION) * (h // 2)))
        )
        bar_bot = (
            ColorClip(size=(w, h // 2), color=(0, 0, 0))
            .with_duration(EYE_DURATION)
            .with_position(lambda t: ("center", (h // 2) + (t / EYE_DURATION) * (h // 2)))
        )

        lbl_l_intro = _make_text_clip(name_l, 70, "white", (w // 3, 120), INTRO_DURATION).with_position((0.05 * w, 0.7 * h))
        lbl_r_intro = _make_text_clip(name_r, 70, "white", (w // 3, 120), INTRO_DURATION).with_position((0.60 * w, 0.7 * h))

        intro_part = CompositeVideoClip(
            [base_image_clip.with_duration(INTRO_DURATION), bar_top, bar_bot, lbl_l_intro, lbl_r_intro],
            size=(w, h)
        )

        # ── PHASE 2 : Vidéo principale ──────────────────────
        vid_dur = video_clip.duration
        lbl_l_vid = _make_text_clip(name_l, 70, "white", (w // 3, 120), vid_dur).with_position((0.05 * w, 0.7 * h))
        lbl_r_vid = _make_text_clip(name_r, 70, "white", (w // 3, 120), vid_dur).with_position((0.60 * w, 0.7 * h))
        subtitles  = _make_text_clip(speech.upper(), 55, "yellow", (int(w * 0.9), 250), vid_dur, stroke_w=4).with_position(("center", 0.75 * h))

        video_part = CompositeVideoClip([video_clip, lbl_l_vid, lbl_r_vid, subtitles], size=(w, h))

        # ── PHASE 3 : Image figée + narration + timer ────────────────────────
        if os.path.exists(paths["narrator"]):
            narrator_audio = AudioFileClip(paths["narrator"])
            freeze_dur = narrator_audio.duration

            btn_a = _make_text_clip(choice_a.upper(), 60, "white", (int(w * 0.45), 150), freeze_dur).with_position((0.02 * w, 0.5 * h))
            btn_b = _make_text_clip(choice_b.upper(), 60, "white", (int(w * 0.45), 150), freeze_dur).with_position((0.53 * w, 0.5 * h))

            T_STEP = 0.5
            TIMER_BEATS = 3
            timer_start = max(0.0, freeze_dur - T_STEP * (TIMER_BEATS + 1))

            countdown = [
                _make_text_clip(label, 250, color, (300, 300), T_STEP)
                .with_start(timer_start + i * T_STEP)
                .with_position(("center", "center"))
                for i, (label, color) in enumerate([("3", "red"), ("2", "orange"), ("1", "green")])
            ]

            audio_elements = [narrator_audio]
            if os.path.exists(paths["tick"]) and os.path.exists(paths["beep"]):
                audio_elements += [
                    AudioFileClip(paths["tick"]).with_start(timer_start),
                    AudioFileClip(paths["tick"]).with_start(timer_start + T_STEP),
                    AudioFileClip(paths["beep"]).with_start(timer_start + 2 * T_STEP),
                ]

            freeze_part = CompositeVideoClip(
                [base_image_clip.with_duration(freeze_dur), btn_a, btn_b, *countdown],
                size=(w, h)
            ).with_audio(CompositeAudioClip(audio_elements))
            
            final_video = concatenate_videoclips([intro_part, video_part, freeze_part], method="compose")
        else:
            final_video = concatenate_videoclips([intro_part, video_part], method="compose")

        final_video.write_videofile(
            paths["output"],
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(project_dir, "temp-audio.m4a"),
            remove_temp=True,
        )

    finally:
        video_clip.close()
        if narrator_audio is not None:
            narrator_audio.close()

    return paths["output"]
