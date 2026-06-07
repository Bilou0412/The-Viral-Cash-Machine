import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, CompositeAudioClip
)
from openai import OpenAI
import replicate
from concurrent.futures import ThreadPoolExecutor
import io

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
    try: font = ImageFont.truetype(os.path.abspath(font_path), int(fontsize))
    except: font = ImageFont.load_default()
    left, top, right, bottom = font.getbbox(text)
    tw, th = right - left, bottom - top
    px, py = int(fontsize * 0.35), int(fontsize * 0.2)
    img_w, img_h = tw + 2 * px, th + 2 * py
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, img_w, img_h], radius=int(fontsize*0.2), fill=(0, 0, 0, 140))
    tx, ty = px - left, py - top
    sw = 4
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx**2 + dy**2 <= sw**2: draw.text((tx + dx, ty + dy), text, font=font, fill=(0, 0, 0, 255))
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    return ImageClip(np.array(img)).with_duration(duration)

def create_circular_timer_pil(label, fontsize, size, duration, font_path="assets/Minecraft.ttf"):
    img_size = int(size)
    img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([5, 5, img_size-5, img_size-5], fill=(0, 0, 0, 220), outline="white", width=6)
    try: font = ImageFont.truetype(os.path.abspath(font_path), int(fontsize))
    except: font = ImageFont.load_default()
    left, top, right, bottom = font.getbbox(label)
    tw, th = right - left, bottom - top
    tx, ty = (img_size - tw)//2 - left, (img_size - th)//2 - top
    draw.text((tx, ty), label, font=font, fill="white")
    return ImageClip(np.array(img)).with_duration(duration)

def create_dark_fantasy_gauge(w, duration):
    gauge_w, gauge_h = int(w * 0.8), 60
    def make_frame(t):
        progress = max(0, 1.0 - (t / duration))
        img = Image.new("RGBA", (gauge_w, gauge_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, gauge_w, gauge_h], outline=(120, 120, 120), width=4)
        draw.rectangle([4, 4, gauge_w-4, gauge_h-4], fill=(20, 5, 5))
        if progress > 0:
            fill_w = int((gauge_w - 8) * progress)
            draw.rectangle([4, 4, 4 + fill_w, gauge_h-4], fill=(160, 0, 0))
            draw.rectangle([4, 4, 4 + fill_w, gauge_h-40], fill=(255, 50, 50, 100))
        return np.array(img)
    from moviepy import VideoClip
    return VideoClip(make_frame, duration=duration)

def _make_text_clip_exact(text, fsize, color, duration, font_path, stroke_w=4):
    try: font = ImageFont.truetype(os.path.abspath(font_path), int(fsize))
    except: font = ImageFont.load_default()
    l, t, r, b = font.getbbox(text)
    tw, th = r - l, b - t
    sw = int(stroke_w)
    img_w, img_h = tw + 2*sw + 10, th + 2*sw + 10
    img = Image.new("RGBA", (img_w, img_h), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    tx, ty = sw + 5 - l, sw + 5 - t
    if sw > 0:
        for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            draw.text((tx+dx*sw, ty+dy*sw), text, font=font, fill="black")
    draw.text((tx, ty), text, font=font, fill=color)
    return ImageClip(np.array(img)).with_duration(duration), img_w, img_h

def detect_side_entity(img_bytes, side_label, full_w, full_h):
    """Analyse un côté de l'image (flux binaire)."""
    try:
        img_file = io.BytesIO(img_bytes)
        output = replicate.run(
            "adirik/grounding-dino:efd10a8ddc57ea28773327e881ce95e20cc1d734c589f7dd01d2036921ed78aa",
            input={
                "image": img_file,
                "query": "the head or highest point of the entity",
                "box_threshold": 0.12,
                "text_threshold": 0.12
            }
        )
        detections = output.get("detections", [])
        if detections:
            # On prend la détection la plus haute
            best = sorted(detections, key=lambda d: d['bbox'][1])[0]
            bbox = best['bbox'] # [x1, y1, x2, y2]
            
            # NORMALISATION HAUTE PRÉCISION
            # Si Replicate renvoie des pixels (> 2.0), on normalise
            # Note: Replicate GroundingDino adirik renvoie souvent des pixels relatifs à l'image envoyée.
            if any(v > 2.0 for v in bbox):
                # On assume que les pixels renvoyés sont à l'échelle de l'image originale 
                # (puisque c'est celle qu'on a envoyée)
                cx = (bbox[0] + bbox[2]) / (2.0 * full_w)
                ty = bbox[1] / full_h
                return cx, ty
            return (bbox[0] + bbox[2]) / 2.0, bbox[1]
    except Exception as e:
        print(f"❌ AI Error ({side_label}): {e}")
    return None

def get_ai_head_positions_split(image_path, instance_dir):
    """Découpe verticalement, sauvegarde les images de test et lance l'IA en parallèle."""
    try:
        print(f"🔍 Starting Parallel Split-Detection for: {image_path}")
        with Image.open(image_path) as full_img:
            w, h = full_img.size
            
            # 1. Préparation Image GAUCHE
            left_mask = full_img.copy()
            draw_l = ImageDraw.Draw(left_mask)
            draw_l.rectangle([w//2, 0, w, h], fill="black") # Cache la droite
            left_path = os.path.join(instance_dir, "debug_split_left.png")
            left_mask.save(left_path)
            
            # 2. Préparation Image DROITE
            right_mask = full_img.copy()
            draw_r = ImageDraw.Draw(right_mask)
            draw_r.rectangle([0, 0, w//2, h], fill="black") # Cache la gauche
            right_path = os.path.join(instance_dir, "debug_split_right.png")
            right_mask.save(right_path)

            # 3. Exécution parallèle
            with ThreadPoolExecutor(max_workers=2) as executor:
                with open(left_path, "rb") as fl, open(right_path, "rb") as fr:
                    f_left = executor.submit(detect_side_entity, fl.read(), "LEFT", w, h)
                    f_right = executor.submit(detect_side_entity, fr.read(), "RIGHT", w, h)
                    
                    res_l = f_left.result()
                    res_r = f_right.result()
                
                final_l = res_l if res_l else (0.25, 0.40)
                final_r = res_r if res_r else (0.75, 0.40)
                return final_l, final_r

    except Exception as e:
        print(f"💥 Split-Detection Critical Failure: {e}")
    return (0.25, 0.40), (0.75, 0.40)

def compile_video(project_name: str, instance_id: str) -> str:
    print(f"\n--- 🎞️ STARTING COMPILATION: {project_name}/{instance_id} ---")
    project_dir = os.path.join("exports", project_name, instance_id)
    paths = {"video": os.path.join(project_dir, "video.mp4"), "image": os.path.join(project_dir, "base_image.png"), "narrator": os.path.join(project_dir, "narrator.mp3"), "metadata": os.path.join(project_dir, "metadata.json"), "output": os.path.join(project_dir, "final_video.mp4"), "tick": os.path.join("assets", "tick.wav"), "beep": os.path.join("assets", "final.wav")}
    if not os.path.exists(paths["video"]) or not os.path.exists(paths["metadata"]): raise FileNotFoundError("Assets manquants.")
    with open(paths["metadata"], "r", encoding="utf-8") as f: meta = json.load(f)

    # --- AI DYNAMIC DETECTION (SPLIT + SAVE DEBUG) ---
    if os.path.exists(paths["image"]):
        hx, hy = meta.get("head_l_x"), meta.get("head_l_y")
        # On ne lance la détection que si les données sont absentes (None) ou aux valeurs par défaut
        if hx is None or (hx == 0.25 and hy == 0.40):
            l_head, r_head = get_ai_head_positions_split(paths["image"], project_dir)
            meta["head_l_x"], meta["head_l_y"] = l_head
            meta["head_r_x"], meta["head_r_y"] = r_head
            with open(paths["metadata"], "w", encoding="utf-8") as f: json.dump(meta, f, indent=4)
            print(f"✅ AI Detection Successful. Coordinates normalized and saved.")

    name_l, name_r = meta.get("char_left_name", "").upper(), meta.get("char_right_name", "").upper()
    char_audio = os.path.join(project_dir, "character.mp3")
    if not os.path.exists(char_audio): char_audio = paths["video"]
    char_subs_raw = get_whisper_subtitles(char_audio)
    narr_subs_raw = get_whisper_subtitles(paths["narrator"]) if os.path.exists(paths["narrator"]) else []
    save_srt(char_subs_raw, os.path.join(project_dir, "character.srt"))
    save_srt(narr_subs_raw, os.path.join(project_dir, "narrator.srt"))

    video_clip = VideoFileClip(paths["video"])
    w, h = video_clip.size
    
    # --- AI DYNAMIC POSITIONING ---
    NAME_FSIZE = 50 
    font_p = "assets/Minecraft.ttf"
    lbl_l_exact, tw_l, th_l = _make_text_clip_exact(name_l, NAME_FSIZE, "white", 99, font_p, stroke_w=3)
    lbl_r_exact, tw_r, th_r = _make_text_clip_exact(name_r, NAME_FSIZE, "white", 99, font_p, stroke_w=3)
    hl_x, hl_y = meta.get("head_l_x", 0.25), meta.get("head_l_y", 0.40)
    hr_x, hr_y = meta.get("head_r_x", 0.75), meta.get("head_r_y", 0.40)
    V_OFFSET = 60
    POS_L = (int(hl_x * w - tw_l / 2), int(hl_y * h - th_l - V_OFFSET))
    POS_R = (int(hr_x * w - tw_r / 2), int(hr_y * h - th_r - V_OFFSET))
    
    if os.path.exists(paths["image"]):
        img_orig_pil = Image.open(paths["image"]).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
        base_img = ImageClip(np.array(img_orig_pil))
        img_for_blur = img_orig_pil.copy()
        draw = ImageDraw.Draw(img_for_blur)
        try: font_pix = ImageFont.truetype(os.path.abspath(font_p), NAME_FSIZE)
        except: font_pix = ImageFont.load_default()
        draw.text((POS_L[0] + tw_l//2, POS_L[1] + th_l//2), name_l, font=font_pix, fill="white", anchor="mm", stroke_width=3, stroke_fill="black")
        draw.text((POS_R[0] + tw_r//2, POS_R[1] + th_r//2), name_r, font=font_pix, fill="white", anchor="mm", stroke_width=3, stroke_fill="black")
        blur_bg_with_names = ImageClip(np.array(img_for_blur.filter(ImageFilter.GaussianBlur(radius=25))))
    else: 
        base_img = ColorClip(size=(w, h), color=(50, 50, 50))
        blur_bg_with_names = ColorClip(size=(w, h), color=(30, 30, 30))

    lbl_l_pers = lbl_l_exact.with_position(POS_L)
    lbl_r_pers = lbl_r_exact.with_position(POS_R)

    # Sequence Montage
    INTRO_DUR, EYE_DUR = 1.2, 0.8
    bar_top = ColorClip(size=(w, h // 2), color=(0,0,0)).with_duration(EYE_DUR).with_position(lambda t: ("center", -(t/EYE_DUR)*(h//2)))
    bar_bot = ColorClip(size=(w, h // 2), color=(0,0,0)).with_duration(EYE_DUR).with_position(lambda t: ("center", (h//2)+(t/EYE_DUR)*(h//2)))
    intro_part = CompositeVideoClip([base_img.with_duration(INTRO_DUR), lbl_l_pers.with_duration(INTRO_DUR), lbl_r_pers.with_duration(INTRO_DUR), bar_top, bar_bot], size=(w, h))

    vid_dur = video_clip.duration
    char_subs = []
    for s in char_subs_raw:
        if s['start'] < vid_dur:
            char_subs.append(create_styled_subtitle_pil(s['text'].upper(), 72, min(s['end'], vid_dur)-s['start']).with_start(s['start']).with_position(("center", 0.78 * h)))
    video_part = CompositeVideoClip([video_clip, lbl_l_pers.with_duration(vid_dur), lbl_r_pers.with_duration(vid_dur), *char_subs], size=(w, h))

    if os.path.exists(paths["narrator"]):
        narrator_audio = AudioFileClip(paths["narrator"])
        narr_dur = narrator_audio.duration
        narr_subs = []
        for s in narr_subs_raw:
            if s['start'] < narr_dur:
                narr_subs.append(create_styled_subtitle_pil(s['text'].upper(), 72, min(s['end'], narr_dur)-s['start']).with_start(s['start']).with_position(("center", 0.78 * h)))
        narration_part = CompositeVideoClip([base_img.with_duration(narr_dur), lbl_l_pers.with_duration(narr_dur), lbl_r_pers.with_duration(narr_dur), *narr_subs], size=(w,h)).with_audio(narrator_audio)
        
        T_STEP = 0.7 
        CHOICE_DUR = T_STEP * 3
        choice_bg = blur_bg_with_names.with_duration(CHOICE_DUR)
        countdown = [create_circular_timer_pil(label, 160, 230, T_STEP).with_start(i * T_STEP).with_position(("center", "center")) for i, label in enumerate(["3","2","1"])]
        dark_gauge = create_dark_fantasy_gauge(w, CHOICE_DUR).with_position(("center", int(0.65 * h)))
        
        choice_audio_el = []
        if os.path.exists(paths["tick"]): 
            for step in [0, T_STEP, 2*T_STEP]: choice_audio_el.append(AudioFileClip(paths["tick"]).with_start(step))
        if os.path.exists(paths["beep"]): choice_audio_el.append(AudioFileClip(paths["beep"]).with_start(CHOICE_DUR))
        
        choice_part = CompositeVideoClip([choice_bg, dark_gauge, *countdown], size=(w,h))
        if choice_audio_el: choice_part = choice_part.with_audio(CompositeAudioClip(choice_audio_el))
        
        final_video = concatenate_videoclips([intro_part, video_part, narration_part, choice_part], method="compose")
    else:
        final_video = concatenate_videoclips([intro_part, video_part], method="compose")

    final_video.write_videofile(paths["output"], fps=24, codec="libx264", audio_codec="aac", temp_audiofile=os.path.join(project_dir, "temp-audio.m4a"), remove_temp=True)
    video_clip.close()
    if 'narrator_audio' in locals(): narrator_audio.close()
    return paths["output"]
