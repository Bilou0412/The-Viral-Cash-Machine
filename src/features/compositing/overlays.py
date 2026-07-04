from dataclasses import dataclass
from typing import Protocol
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, VideoClip


class Overlay(Protocol):
    """Port for video overlays (subtitles, timers, nameplates, etc.)."""

    def to_clip(self, canvas: tuple[int, int]) -> ImageClip | VideoClip:
        """Render overlay as a MoviePy Clip."""
        ...


@dataclass(frozen=True)
class SubtitleOverlay:
    """Subtitle text with styling."""

    text: str
    fontsize: int = 24
    duration: float = 1.0
    font_path: str = "assets/montserrat.bold.ttf"

    def to_clip(self, canvas: tuple[int, int]) -> ImageClip:
        """Create styled subtitle clip."""
        try:
            font = ImageFont.truetype(os.path.abspath(self.font_path), int(self.fontsize))
        except Exception:
            font = ImageFont.load_default()

        left, top, right, bottom = font.getbbox(self.text)
        tw, th = right - left, bottom - top
        px, py = int(self.fontsize * 0.35), int(self.fontsize * 0.2)
        img_w, img_h = tw + 2 * px, th + 2 * py
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [0, 0, img_w, img_h],
            radius=int(self.fontsize * 0.2),
            fill=(0, 0, 0, 140),
        )
        tx, ty = px - left, py - top
        sw = 4
        for dx in range(-sw, sw + 1):
            for dy in range(-sw, sw + 1):
                if dx**2 + dy**2 <= sw**2:
                    draw.text((tx + dx, ty + dy), self.text, font=font, fill=(0, 0, 0, 255))
        draw.text((tx, ty), self.text, font=font, fill=(255, 255, 255, 255))
        return ImageClip(np.array(img)).with_duration(self.duration)


@dataclass(frozen=True)
class TimerOverlay:
    """Circular countdown timer."""

    label: str
    fontsize: int = 48
    size: float = 200
    duration: float = 1.0
    font_path: str = "assets/Minecraft.ttf"

    def to_clip(self, canvas: tuple[int, int]) -> ImageClip:
        """Create circular timer clip."""
        img_size = int(self.size)
        img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([5, 5, img_size - 5, img_size - 5], fill=(0, 0, 0, 220), outline="white", width=6)

        try:
            font = ImageFont.truetype(os.path.abspath(self.font_path), int(self.fontsize))
        except Exception:
            font = ImageFont.load_default()

        left, top, right, bottom = font.getbbox(self.label)
        tw, th = right - left, bottom - top
        tx, ty = (img_size - tw) // 2 - left, (img_size - th) // 2 - top
        draw.text((tx, ty), self.label, font=font, fill="white")
        return ImageClip(np.array(img)).with_duration(self.duration)


@dataclass(frozen=True)
class GaugeOverlay:
    """Dark fantasy-themed progress gauge."""

    width: float
    duration: float = 1.0

    def to_clip(self, canvas: tuple[int, int]) -> VideoClip:
        """Create animated gauge clip."""
        gauge_w, gauge_h = int(self.width * 0.8), 60

        def make_frame(t: float) -> np.ndarray:
            progress = max(0, 1.0 - (t / self.duration))
            img = Image.new("RGBA", (gauge_w, gauge_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rectangle(
                [0, 0, gauge_w, gauge_h], outline=(120, 120, 120), width=4
            )
            draw.rectangle([4, 4, gauge_w - 4, gauge_h - 4], fill=(20, 5, 5))
            if progress > 0:
                fill_w = int((gauge_w - 8) * progress)
                draw.rectangle([4, 4, 4 + fill_w, gauge_h - 4], fill=(160, 0, 0))
                draw.rectangle(
                    [4, 4, 4 + fill_w, gauge_h - 40], fill=(255, 50, 50, 100)
                )
            return np.array(img)

        return VideoClip(make_frame, duration=self.duration)


@dataclass(frozen=True)
class NameplateOverlay:
    """Character nameplate with position."""

    text: str
    fontsize: int = 50
    color: str = "white"
    duration: float = 1.0
    font_path: str = "assets/Minecraft.ttf"
    stroke_width: int = 4
    pos: tuple[int, int] = (0, 0)  # Coordinates already resolved

    def to_clip(self, canvas: tuple[int, int]) -> ImageClip:
        """Create nameplate clip."""
        try:
            font = ImageFont.truetype(os.path.abspath(self.font_path), int(self.fontsize))
        except Exception:
            font = ImageFont.load_default()

        left, top, right, bottom = font.getbbox(self.text)
        tw, th = right - left, bottom - top
        sw = int(self.stroke_width)
        img_w, img_h = tw + 2 * sw + 10, th + 2 * sw + 10
        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        tx, ty = sw + 5 - left, sw + 5 - top

        if sw > 0:
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text(
                    (tx + dx * sw, ty + dy * sw), self.text, font=font, fill="black"
                )
        draw.text((tx, ty), self.text, font=font, fill=self.color)
        return ImageClip(np.array(img)).with_duration(self.duration)
