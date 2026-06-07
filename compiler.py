import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, CompositeAudioClip
)
from openai import OpenAI

def get_whisper_subtitles(file_path):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not os.path.exists(file_path): 
        print(f"Whisper skipped: API Key? {bool(api_key)}, File? {os.path.exists(file_path)}")
        return []
    try:
        client = OpenAI(api_key=api_key)
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        subs = []
        # We strictly want words for the TikTok effect
        raw_words = []
        if hasattr(transcript, 'words') and transcript.words:
            raw_words = transcript.words
        elif hasattr(transcript, 'segments') and transcript.segments:
            # If for some reason word-level is missing, we simulate it by splitting segments
            # This ensures we always have the dynamic effect requested
            for seg in transcript.segments:
                words_in_seg = seg.text.strip().split()
                if not words_in_seg: continue
                dur = seg.end - seg.start
                word_dur = dur / len(words_in_seg)
                for i, w in enumerate(words_in_seg):
                    subs.append({
                        "text": w.strip(),
                        "start": seg.start + (i * word_dur),
                        "end": seg.start + ((i + 1) * word_dur)
                    })
            print(f"Whisper: Simulated {len(subs)} words from segments.")
            return subs
            
        for item in raw_words:
            text_val = item.word if hasattr(item, 'word') else getattr(item, 'text', "")
            if text_val:
                subs.append({
                    "text": text_val.strip(),
                    "start": item.start,
                    "end": item.end
                })
        print(f"Whisper success: {len(subs)} words found for {file_path}")
        return subs
    except Exception as e:
        print(f"Whisper failed for {file_path}: {e}")
        return []

def format_timestamp(seconds):
    """Convertit des secondes en format SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def save_srt(subs_data, output_path):
    """Enregistre les données Whisper au format .srt"""
    if not subs_data: return
    with open(output_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(subs_data, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n")
            f.write(f"{s['text']}\n\n")
    print(f"SRT saved to {output_path}")

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
    Compile les assets d'un projet en une vidéo finale avec sous-titres synchronisés via Whisper.
    Génère les sous-titres à la volée pendant la compilation.
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

    # Extraction des données (Stricte conformité aux métadonnées)
    name_l = meta.get("char_left_name", "")
    name_r = meta.get("char_right_name", "")
    choice_a = meta.get("choice_a", name_l)
    choice_b = meta.get("choice_b", name_r)
    
    # Generate Subtitles on-the-fly during compilation
    print("✍️ Transcribing audio for synced subtitles...")
    # intro video usually contains the character speech
    # other parts might have character.mp3
    char_audio_path = os.path.join(project_dir, "character.mp3")
    if not os.path.exists(char_audio_path):
        char_audio_path = paths["video"]
        
    char_subs_data = get_whisper_subtitles(char_audio_path)
    narr_subs_data = get_whisper_subtitles(paths["narrator"]) if os.path.exists(paths["narrator"]) else []

    # Exportation physique des fichiers SRT
    save_srt(char_subs_data, os.path.join(project_dir, "character.srt"))
    save_srt(narr_subs_data, os.path.join(project_dir, "narrator.srt"))

    video_clip = VideoFileClip(paths["video"])
    narrator_audio = None

    try:
        w, h = video_clip.size

        # --- PREPARATION DE L'IMAGE ---
        if os.path.exists(paths["image"]):
            img_pil = Image.open(paths["image"]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
            base_image_clip = ImageClip(np.array(img_pil))
        else:
            base_image_clip = ColorClip(size=(w, h), color=(50, 50, 50))

        # ── PHASE 1 : OUVERTURE DES YEUX (2.0s) ──────────────────
        INTRO_DURATION = 2.0
        EYE_DURATION   = 0.8
        bar_top = (ColorClip(size=(w, h // 2), color=(0, 0, 0)).with_duration(EYE_DURATION).with_position(lambda t: ("center", -(t / EYE_DURATION) * (h // 2))))
        bar_bot = (ColorClip(size=(w, h // 2), color=(0, 0, 0)).with_duration(EYE_DURATION).with_position(lambda t: ("center", (h // 2) + (t / EYE_DURATION) * (h // 2))))
        lbl_l_intro = _make_text_clip(name_l, 70, "white", (w // 3, 120), INTRO_DURATION).with_position((0.05 * w, 0.7 * h))
        lbl_r_intro = _make_text_clip(name_r, 70, "white", (w // 3, 120), INTRO_DURATION).with_position((0.60 * w, 0.7 * h))
        intro_part = CompositeVideoClip([base_image_clip.with_duration(INTRO_DURATION), bar_top, bar_bot, lbl_l_intro, lbl_r_intro], size=(w, h))

        # ── PHASE 2 : VIDÉO PRINCIPALE AVEC SOUS-TITRES SYNCHROS ──────────────────────
        vid_dur = video_clip.duration
        lbl_l_vid = _make_text_clip(name_l, 70, "white", (w // 3, 120), vid_dur).with_position((0.05 * w, 0.7 * h))
        lbl_r_vid = _make_text_clip(name_r, 70, "white", (w // 3, 120), vid_dur).with_position((0.60 * w, 0.7 * h))
        
        # Build synced subtitles list
        char_subs = []
        if char_subs_data:
            for s in char_subs_data:
                txt = s['text'].upper()
                if s['start'] < vid_dur:
                    end_time = min(s['end'], vid_dur)
                    char_subs.append(
                        _make_text_clip(txt, 55, "yellow", (int(w * 0.9), 250), end_time - s['start'], stroke_w=4)
                        .with_start(s['start'])
                        .with_position(("center", 0.75 * h))
                    )
        else:
            speech = meta.get("character_speech", "")
            char_subs.append(_make_text_clip(speech.upper(), 55, "yellow", (int(w * 0.9), 250), vid_dur, stroke_w=4).with_position(("center", 0.75 * h)))

        video_part = CompositeVideoClip([video_clip, lbl_l_vid, lbl_r_vid, *char_subs], size=(w, h))

        # ── PHASE 3 : IMAGE FIGÉE + NARRATION SYNCHRONISÉE ────────────────────────
        if os.path.exists(paths["narrator"]):
            narrator_audio = AudioFileClip(paths["narrator"])
            freeze_dur = narrator_audio.duration
            choice_a = meta.get("choice_a", name_l).upper()
            choice_b = meta.get("choice_b", name_r).upper()
            btn_a = _make_text_clip(choice_a, 60, "white", (int(w * 0.45), 150), freeze_dur).with_position((0.02 * w, 0.5 * h))
            btn_b = _make_text_clip(choice_b, 60, "white", (int(w * 0.45), 150), freeze_dur).with_position((0.53 * w, 0.5 * h))

            narr_subs = []
            for s in narr_subs_data:
                txt = s['text'].upper()
                if s['start'] < freeze_dur:
                    end_time = min(s['end'], freeze_dur)
                    narr_subs.append(
                        _make_text_clip(txt, 50, "white", (int(w * 0.8), 200), end_time - s['start'], stroke_w=3)
                        .with_start(s['start'])
                        .with_position(("center", 0.85 * h))
                    )

            T_STEP = 0.5
            timer_start = max(0.0, freeze_dur - T_STEP * 4)
            countdown = [
                _make_text_clip(label, 250, color, (300, 300), T_STEP).with_start(timer_start + i * T_STEP).with_position(("center", "center"))
                for i, (label, color) in enumerate([("3", "red"), ("2", "orange"), ("1", "green")])
            ]

            audio_elements = [narrator_audio]
            tick_path, beep_path = paths["tick"], paths["beep"]
            if os.path.exists(tick_path):
                audio_elements.append(AudioFileClip(tick_path).with_start(timer_start))
                audio_elements.append(AudioFileClip(tick_path).with_start(timer_start + T_STEP))
            if os.path.exists(beep_path):
                audio_elements.append(AudioFileClip(beep_path).with_start(timer_start + 2 * T_STEP))

            freeze_part = CompositeVideoClip(
                [base_image_clip.with_duration(freeze_dur), btn_a, btn_b, *narr_subs, *countdown],
                size=(w, h)
            ).with_audio(CompositeAudioClip(audio_elements))
            
            final_video = concatenate_videoclips([intro_part, video_part, freeze_part], method="compose")
        else:
            final_video = concatenate_videoclips([intro_part, video_part], method="compose")

        final_video.write_videofile(paths["output"], fps=24, codec="libx264", audio_codec="aac", temp_audiofile=os.path.join(project_dir, "temp-audio.m4a"), remove_temp=True)

    finally:
        video_clip.close()
        if narrator_audio: narrator_audio.close()

    return paths["output"]
