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
    if not api_key or not os.path.exists(file_path): return []
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
        if hasattr(transcript, 'words') and transcript.words:
            raw_words = transcript.words
        elif hasattr(transcript, 'segments') and transcript.segments:
            for seg in transcript.segments:
                words_in_seg = seg.text.strip().split()
                if not words_in_seg: continue
                dur = seg.end - seg.start
                word_dur = dur / len(words_in_seg)
                for i, w in enumerate(words_in_seg):
                    subs.append({"text": w.strip(), "start": seg.start + (i * word_dur), "end": seg.start + ((i + 1) * word_dur)})
            return subs
        else: return []
        for item in raw_words:
            text_val = item.word if hasattr(item, 'word') else getattr(item, 'text', "")
            if text_val: subs.append({"text": text_val.strip(), "start": item.start, "end": item.end})
        return subs
    except Exception as e:
        print(f"Whisper failed for {file_path}: {e}")
        return []

def format_timestamp(seconds):
    h, m, s = int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def save_srt(subs_data, output_path):
    if not subs_data: return
    with open(output_path, "w", encoding="utf-8") as f:
        for i, s in enumerate(subs_data, 1):
            f.write(f"{i}\n{format_timestamp(s['start'])} --> {format_timestamp(s['end'])}\n{s['text']}\n\n")

def create_styled_subtitle_pil(text, fontsize, duration, font_path="assets/montserrat.bold.ttf"):
    """Crée un petit badge texte englobé par un fond noir arrondi (55% opacité)."""
    try:
        font = ImageFont.truetype(os.path.abspath(font_path), int(fontsize))
    except:
        font = ImageFont.load_default()
        
    # Mesure précise du texte pour créer une boîte à la bonne taille
    # On utilise getmask().getbbox() pour ignorer les espaces vides inutiles
    left, top, right, bottom = font.getbbox(text)
    tw = right - left
    th = bottom - top
    
    # Padding dynamique
    px, py = int(fontsize * 0.35), int(fontsize * 0.2)
    
    # Taille de l'image finale (badge)
    img_w, img_h = tw + 2 * px, th + 2 * py
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Fond noir arrondi (55% opacité = 140)
    draw.rounded_rectangle([0, 0, img_w, img_h], radius=int(fontsize*0.2), fill=(0, 0, 0, 140))
    
    # Position du texte centrée dans son badge
    # On compense l'offset 'top' et 'left' renvoyé par getbbox
    tx, ty = px - left, py - top
    
    # Contour noir 4px (méthode robuste)
    sw = 4
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx**2 + dy**2 <= sw**2:
                draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))
    
    # Texte blanc final
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    
    return ImageClip(np.array(img)).with_duration(duration)

def _make_text_clip(text, fsize, color, box_size, duration, stroke_w=3, font="Minecraft", fade_in=0):
    font_p = "assets/Minecraft.ttf" if font in ["Pixel", "Minecraft"] else "C:\\Windows\\Fonts\\arial.ttf"
    if font == "Minecraft" and not os.path.exists(font_p): font_p = "assets/KiwiSoda.ttf"
    try:
        clip = TextClip(text=text, font_size=int(fsize), color=color, size=(int(box_size[0]), int(box_size[1])), font=os.path.abspath(font_p), stroke_color="black", stroke_width=int(stroke_w)).with_duration(duration)
    except:
        # Fallback PIL manuel (redimensionnement en entier pour éviter TypeError)
        bs = (int(box_size[0]), int(box_size[1]))
        img = Image.new("RGBA", bs, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        try: f = ImageFont.truetype(os.path.abspath(font_p), int(fsize))
        except: f = ImageFont.load_default()
        bl, bt, br, bb = draw.textbbox((0,0), text, font=f)
        txt_x, txt_y = (bs[0]-(br-bl))//2, (bs[1]-(bb-bt))//2
        if stroke_w > 0:
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]: draw.text((txt_x+dx*stroke_w, txt_y+dy*stroke_w), text, font=f, fill="black")
        draw.text((txt_x, txt_y), text, font=f, fill=color)
        clip = ImageClip(np.array(img)).with_duration(duration)
    
    if fade_in > 0:
        try:
            from moviepy.video.fx import CrossFadeIn
            clip = clip.with_effects([CrossFadeIn(fade_in)])
        except:
            clip = clip.with_effects([lambda c: c.with_mask(c.mask.multiply(lambda t: min(1, t/fade_in)))])
    return clip

def compile_video(project_name: str, instance_id: str) -> str:
    project_dir = os.path.join("exports", project_name, instance_id)
    paths = {"video": os.path.join(project_dir, "video.mp4"), "image": os.path.join(project_dir, "base_image.png"), "narrator": os.path.join(project_dir, "narrator.mp3"), "metadata": os.path.join(project_dir, "metadata.json"), "output": os.path.join(project_dir, "final_video.mp4"), "tick": os.path.join("assets", "tick.wav"), "beep": os.path.join("assets", "final.wav")}
    if not os.path.exists(paths["video"]) or not os.path.exists(paths["metadata"]): raise FileNotFoundError("Assets manquants.")
    with open(paths["metadata"], "r", encoding="utf-8") as f: meta = json.load(f)

    name_l, name_r = meta.get("char_left_name", ""), meta.get("char_right_name", "")
    char_audio = os.path.join(project_dir, "character.mp3")
    if not os.path.exists(char_audio): char_audio = paths["video"]
    char_subs_raw = get_whisper_subtitles(char_audio)
    narr_subs_raw = get_whisper_subtitles(paths["narrator"]) if os.path.exists(paths["narrator"]) else []
    save_srt(char_subs_raw, os.path.join(project_dir, "character.srt"))
    save_srt(narr_subs_raw, os.path.join(project_dir, "narrator.srt"))

    video_clip = VideoFileClip(paths["video"])
    w, h = video_clip.size
    POS_L, POS_R, BOX_NAME = (0.02 * w, 0.7 * h), (0.48 * w, 0.7 * h), (w // 2, 200)

    if os.path.exists(paths["image"]):
        img_p = Image.open(paths["image"]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
        base_img = ImageClip(np.array(img_p))
    else: base_img = ColorClip(size=(w, h), color=(50, 50, 50))

    # PHASE 1 : INTRO
    INTRO_DUR, EYE_DUR = 2.0, 0.8
    bar_top = ColorClip(size=(w, h // 2), color=(0,0,0)).with_duration(EYE_DUR).with_position(lambda t: ("center", -(t/EYE_DUR)*(h//2)))
    bar_bot = ColorClip(size=(w, h // 2), color=(0,0,0)).with_duration(EYE_DUR).with_position(lambda t: ("center", (h//2)+(t/EYE_DUR)*(h//2)))
    lbl_l_intro = _make_text_clip(name_l, 100, "white", BOX_NAME, INTRO_DUR, font="Minecraft", fade_in=1.8).with_position(POS_L)
    lbl_r_intro = _make_text_clip(name_r, 100, "white", BOX_NAME, INTRO_DUR, font="Minecraft", fade_in=1.8).with_position(POS_R)
    intro_part = CompositeVideoClip([base_img.with_duration(INTRO_DUR), bar_top, bar_bot, lbl_l_intro, lbl_r_intro], size=(w, h))

    # PHASE 2 : VIDEO (Sous-titres "Badges" Montserrat)
    vid_dur = video_clip.duration
    lbl_l_vid = _make_text_clip(name_l, 100, "white", BOX_NAME, vid_dur, font="Minecraft").with_position(POS_L)
    lbl_r_vid = _make_text_clip(name_r, 100, "white", BOX_NAME, vid_dur, font="Minecraft").with_position(POS_R)
    
    char_subs = []
    for s in char_subs_raw:
        if s['start'] < vid_dur:
            badge = create_styled_subtitle_pil(s['text'].upper(), 72, min(s['end'], vid_dur)-s['start'])
            char_subs.append(badge.with_start(s['start']).with_position(("center", 0.68 * h)))
            
    video_part = CompositeVideoClip([video_clip, lbl_l_vid, lbl_r_vid, *char_subs], size=(w, h))

    # PHASE 3 : FREEZE
    if os.path.exists(paths["narrator"]):
        narrator_audio = AudioFileClip(paths["narrator"])
        freeze_dur = narrator_audio.duration
        btn_a = _make_text_clip(meta.get("choice_a", "").upper(), 70, "white", (int(w*0.48), 180), freeze_dur, font="Minecraft").with_position((0.01*w, 0.5*h))
        btn_b = _make_text_clip(meta.get("choice_b", "").upper(), 70, "white", (int(w*0.48), 180), freeze_dur, font="Minecraft").with_position((0.51*w, 0.5*h))
        
        narr_subs = []
        for s in narr_subs_raw:
            if s['start'] < freeze_dur:
                badge = create_styled_subtitle_pil(s['text'].upper(), 72, min(s['end'], freeze_dur)-s['start'])
                narr_subs.append(badge.with_start(s['start']).with_position(("center", 0.68 * h)))
        
        t_start = max(0.0, freeze_dur - 2.0)
        countdown = [_make_text_clip(l, 250, c, (300, 300), 0.5, font="Minecraft").with_start(t_start + i*0.5).with_position(("center", "center")) for i, (l, c) in enumerate([("3","red"), ("2","orange"), ("1","green")])]
        audio_el = [narrator_audio]
        if os.path.exists(paths["tick"]): audio_el.extend([AudioFileClip(paths["tick"]).with_start(t_start), AudioFileClip(paths["tick"]).with_start(t_start + 0.5)])
        if os.path.exists(paths["beep"]): audio_el.append(AudioFileClip(paths["beep"]).with_start(t_start + 1.0))
        
        freeze_part = CompositeVideoClip([base_img.with_duration(freeze_dur), btn_a, btn_b, *narr_subs, *countdown], size=(w,h)).with_audio(CompositeAudioClip(audio_el))
        final_video = concatenate_videoclips([intro_part, video_part, freeze_part], method="compose")
    else:
        final_video = concatenate_videoclips([intro_part, video_part], method="compose")

    final_video.write_videofile(paths["output"], fps=24, codec="libx264", audio_codec="aac", temp_audiofile=os.path.join(project_dir, "temp-audio.m4a"), remove_temp=True)
    video_clip.close()
    if 'narrator_audio' in locals(): narrator_audio.close()
    return paths["output"]
