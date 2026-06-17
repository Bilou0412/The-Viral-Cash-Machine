"""MoviePyRenderEngine — interprète un VideoSpec résolu et produit le MP4.

C'est le **pont structure → vidéo** (SPEC §5, « trou #1 ») : jusqu'ici le
VideoSpec n'était qu'une donnée dérivée ; ce moteur le *consomme* et rend le
fichier final, en réutilisant les overlays existants (sous-titres, timer, jauge,
nameplates). Il implémente le port `RenderEngine` de `ports.py` et ne voit que :

- le `VideoSpec` (la timeline déclarative), et
- des `ResolvedAssets` (chemins de fichiers sur disque + transcripts + têtes).

Aucun appel réseau, aucune génération : tout est déjà résolu en amont (par un
AssetResolver — réel via Replicate, ou `FakeAssetResolver` pour les tests/CI).

Imports lourds (moviepy/PIL/numpy) volontairement au niveau module : ce fichier
n'est importé QUE par le chemin de rendu, jamais par `videospec/__init__.py`
(garde les imports optionnels paresseux).
"""

from __future__ import annotations

import os
from typing import Any, List, Mapping, Sequence, Tuple

import numpy as np
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
from PIL import Image, ImageFilter, ImageFont

from .models import (
    AbsolutePosition,
    CountdownSegment,
    FootageSegment,
    HeadAnchor,
    IntroSegment,
    NameplateSpec,
    NarrationSegment,
    Segment,
    SubtitleStyle,
    VideoSpec,
)
from .ports import ResolvedAssets
from ..features.compositing.overlays import (
    GaugeOverlay,
    NameplateOverlay,
    SubtitleOverlay,
    TimerOverlay,
)

# Positions de tête par défaut (normalisées) quand le resolve n'en fournit pas.
_DEFAULT_HEADS: Mapping[str, Tuple[float, float]] = {
    "left": (0.3, 0.4),
    "right": (0.7, 0.4),
}


def _text_dims(text: str, fontsize: int, font_path: str, stroke_width: int) -> Tuple[int, int]:
    """Dimensions de l'image d'un nameplate (miroir de NameplateOverlay.to_clip)."""
    try:
        font: ImageFont.FreeTypeFont = ImageFont.truetype(
            os.path.abspath(font_path), int(fontsize)
        )
    except Exception:
        font = ImageFont.load_default()  # type: ignore[assignment]
    l, t, r, b = font.getbbox(text)
    tw, th = r - l, b - t
    sw = int(stroke_width)
    return int(tw + 2 * sw + 10), int(th + 2 * sw + 10)


class MoviePyRenderEngine:
    """Implémente `RenderEngine` : VideoSpec + ResolvedAssets -> fichier MP4."""

    def render(
        self, spec: VideoSpec, resolved: ResolvedAssets, output_path: str
    ) -> str:
        w, h, fps = spec.canvas.width, spec.canvas.height, spec.canvas.fps
        heads = dict(_DEFAULT_HEADS)
        heads.update(resolved.heads)

        clips = [
            self._segment_clip(seg, resolved, w, h, heads) for seg in spec.segments
        ]
        final = concatenate_videoclips(clips, method="compose")

        out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        os.makedirs(out_dir, exist_ok=True)
        final.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(out_dir, "temp-audio.m4a"),
            remove_temp=True,
            logger=None,
        )
        final.close()
        return output_path

    # -- helpers ------------------------------------------------------------

    def _img(self, path: str, w: int, h: int, blur: float = 0.0) -> Image.Image:
        pil = Image.open(path).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
        if blur > 0:
            pil = pil.filter(ImageFilter.GaussianBlur(radius=blur))
        return pil

    def _nameplate_pos(
        self,
        np_spec: NameplateSpec,
        w: int,
        h: int,
        heads: Mapping[str, Tuple[float, float]],
    ) -> Tuple[int, int]:
        text = np_spec.text.upper() if np_spec.uppercase else np_spec.text
        tw, th = _text_dims(text, np_spec.fontsize, np_spec.font_path, np_spec.stroke_width)
        place = np_spec.placement
        if isinstance(place, AbsolutePosition):
            return int(place.x * w), int(place.y * h)
        # HeadAnchor : centré horizontalement sur la tête, au-dessus d'elle.
        hx, hy = heads.get(place.side, _DEFAULT_HEADS[place.side])
        x = int(hx * w - tw / 2)
        y = int(hy * h - th - place.v_offset)
        x = max(5, min(w - tw - 5, x))
        y = max(5, min(h - th - 5, y))
        return x, y

    def _nameplate_clips(
        self,
        nameplates: Sequence[NameplateSpec],
        w: int,
        h: int,
        heads: Mapping[str, Tuple[float, float]],
        duration: float,
    ) -> List[object]:
        out: List[object] = []
        for np_spec in nameplates:
            text = np_spec.text.upper() if np_spec.uppercase else np_spec.text
            pos = self._nameplate_pos(np_spec, w, h, heads)
            clip = (
                NameplateOverlay(
                    text=text,
                    fontsize=np_spec.fontsize,
                    color=np_spec.color,
                    duration=duration,
                    font_path=np_spec.font_path,
                    stroke_width=np_spec.stroke_width,
                )
                .to_clip((w, h))
                .with_position(pos)
                .with_duration(duration)
            )
            out.append(clip)
        return out

    def _subtitle_clips(
        self,
        words: Sequence[Mapping[str, Any]],
        duration: float,
        w: int,
        h: int,
        style: SubtitleStyle,
    ) -> List[object]:
        out: List[object] = []
        for s in words:
            start = float(s["start"])
            if start >= duration:
                continue
            text = s["text"].upper() if style.uppercase else s["text"]
            badge = (
                SubtitleOverlay(
                    text=text,
                    fontsize=style.fontsize,
                    duration=max(0.05, min(float(s["end"]), duration) - start),
                    font_path=style.font_path,
                )
                .to_clip((w, h))
                .with_start(start)
                .with_position(("center", style.y * h))
            )
            out.append(badge)
        return out

    def _segment_clip(
        self,
        seg: Segment,
        resolved: ResolvedAssets,
        w: int,
        h: int,
        heads: Mapping[str, Tuple[float, float]],
    ) -> object:
        paths = resolved.paths
        if isinstance(seg, IntroSegment):
            dur = seg.duration
            bg = ImageClip(np.array(self._img(paths[seg.background], w, h))).with_duration(dur)
            layers: List[object] = [bg]
            layers += self._nameplate_clips(seg.nameplates, w, h, heads, dur)
            if seg.transition is not None:
                eye = seg.transition.duration
                bar_top = (
                    ColorClip(size=(w, h // 2), color=(0, 0, 0))
                    .with_duration(eye)
                    .with_position(lambda t: ("center", -(t / eye) * (h // 2)))
                )
                bar_bot = (
                    ColorClip(size=(w, h // 2), color=(0, 0, 0))
                    .with_duration(eye)
                    .with_position(lambda t: ("center", (h // 2) + (t / eye) * (h // 2)))
                )
                layers += [bar_top, bar_bot]
            return CompositeVideoClip(layers, size=(w, h))

        if isinstance(seg, FootageSegment):
            vclip = VideoFileClip(paths[seg.video]).with_effects([Resize(new_size=(w, h))])
            dur = seg.duration if seg.duration is not None else vclip.duration
            vclip = vclip.with_duration(dur)
            layers = [vclip]
            layers += self._nameplate_clips(seg.nameplates, w, h, heads, dur)
            if seg.subtitles is not None:
                words = resolved.transcripts.get(seg.subtitles.source, ())
                layers += self._subtitle_clips(words, dur, w, h, seg.subtitles.style)
            return CompositeVideoClip(layers, size=(w, h))

        if isinstance(seg, NarrationSegment):
            audio = AudioFileClip(paths[seg.audio])
            dur = seg.duration if seg.duration is not None else audio.duration
            bg = ImageClip(np.array(self._img(paths[seg.background], w, h))).with_duration(dur)
            if seg.zoom is not None:
                zf, zt = seg.zoom.scale_from, seg.zoom.scale_to
                bg = bg.with_effects(
                    [Resize(lambda t: zf + (zt - zf) * (t / dur))]
                ).with_position("center")
            layers = [bg]
            layers += self._nameplate_clips(seg.nameplates, w, h, heads, dur)
            if seg.subtitles is not None:
                words = resolved.transcripts.get(seg.subtitles.source, ())
                layers += self._subtitle_clips(words, dur, w, h, seg.subtitles.style)
            return CompositeVideoClip(layers, size=(w, h)).with_audio(audio)

        if isinstance(seg, CountdownSegment):
            dur = seg.step_duration * len(seg.steps)
            bg = ImageClip(
                np.array(self._img(paths[seg.background], w, h, blur=seg.blur_radius))
            ).with_duration(dur)
            layers = [bg]
            if seg.gauge is not None:
                gauge = (
                    GaugeOverlay(width=w, duration=dur)
                    .to_clip((w, h))
                    .with_position(("center", int(seg.gauge.y * h)))
                )
                layers.append(gauge)
            for i, label in enumerate(seg.steps):
                layers.append(
                    TimerOverlay(
                        label=label,
                        fontsize=seg.timer.fontsize,
                        size=seg.timer.size,
                        duration=seg.step_duration,
                        font_path=seg.timer.font_path,
                    )
                    .to_clip((w, h))
                    .with_start(i * seg.step_duration)
                    .with_position(("center", "center"))
                )
            layers += self._nameplate_clips(seg.nameplates, w, h, heads, dur)
            comp = CompositeVideoClip(layers, size=(w, h))

            audio_el: List[object] = []
            if seg.tick_sound is not None and seg.tick_sound in paths:
                for i in range(len(seg.steps)):
                    audio_el.append(
                        AudioFileClip(paths[seg.tick_sound]).with_start(i * seg.step_duration)
                    )
            if seg.end_sound is not None and seg.end_sound in paths:
                audio_el.append(AudioFileClip(paths[seg.end_sound]).with_start(dur))
            if audio_el:
                comp = comp.with_audio(CompositeAudioClip(audio_el))
            return comp

        raise TypeError(f"Segment non supporté : {type(seg).__name__}")
