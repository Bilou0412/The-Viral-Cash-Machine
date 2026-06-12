import os
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    VideoFileClip, ImageClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, CompositeAudioClip
)
from moviepy.video.fx import Resize, Loop
from openai import OpenAI
import replicate
from concurrent.futures import ThreadPoolExecutor
import io
from features.transcription.ports import Transcriber
from features.transcription.whisper import WhisperTranscriber
from features.compositing.srt import save_srt, format_timestamp
from features.compositing.overlays import (
    Overlay,
    SubtitleOverlay,
    TimerOverlay,
    GaugeOverlay,
    NameplateOverlay,
)
from features.compositing.heads import HeadDetector, GroundingDINOHeadDetector
from features.compositing.compositor import RawVideoCompositor
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

def compile_video_raw(
    project_name: str,
    instance_id: str,
    transcriber: Transcriber | None = None,
    head_detector: HeadDetector | None = None,
) -> str:
    """Compile raw video from assets and metadata."""
    if transcriber is None:
        transcriber = WhisperTranscriber()
    if head_detector is None:
        head_detector = GroundingDINOHeadDetector()

    compositor = RawVideoCompositor(transcriber, head_detector)
    return compositor.compose(project_name, instance_id)
