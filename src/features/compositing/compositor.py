"""Video composition orchestration."""

import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    ColorClip,
    concatenate_videoclips,
    CompositeVideoClip,
    CompositeAudioClip,
)
from moviepy.video.fx import Resize

from ..transcription.ports import Transcriber
from .heads import HeadDetector
from .srt import save_srt
from .overlays import SubtitleOverlay, TimerOverlay, GaugeOverlay, NameplateOverlay


class RawVideoCompositor:
    """Orchestrates video composition with injected dependencies."""

    def __init__(self, transcriber: Transcriber, head_detector: HeadDetector):
        self.transcriber = transcriber
        self.head_detector = head_detector

    def compose(
        self,
        project_name: str,
        instance_id: str,
        char_left_name: str,
        char_right_name: str,
        head_l_x: float,
        head_l_y: float,
        head_r_x: float,
        head_r_y: float,
    ) -> str:
        """Compose raw video from assets with immutable parameters.

        Args:
            project_name: Project directory name
            instance_id: Instance directory name
            char_left_name: Left character name
            char_right_name: Right character name
            head_l_x: Left head x position (0-1)
            head_l_y: Left head y position (0-1)
            head_r_x: Right head x position (0-1)
            head_r_y: Right head y position (0-1)

        Returns:
            Path to final_video.mp4
        """
        print(f"\n--- 🎞️ STARTING RAW COMPILATION: {project_name}/{instance_id} ---")

        base = os.environ.get("VCM_OUTPUT_DIR", "exports")
        project_dir = os.path.join(base, project_name, instance_id)
        paths = {
            "video": os.path.join(project_dir, "video.mp4"),
            "image": os.path.join(project_dir, "base_image.png"),
            "narrator": os.path.join(project_dir, "narrator.mp3"),
            "output": os.path.join(project_dir, "final_video.mp4"),
            "tick": os.path.join("assets", "tick.wav"),
            "beep": os.path.join("assets", "final.wav"),
        }

        if not os.path.exists(paths["video"]):
            raise FileNotFoundError("Assets manquants.")

        # Use immutable parameters
        hl_x, hl_y = head_l_x, head_l_y
        hr_x, hr_y = head_r_x, head_r_y
        name_l = char_left_name.upper()
        name_r = char_right_name.upper()

        # Transcribe and save subtitles
        char_audio = os.path.join(project_dir, "character.mp3")
        if not os.path.exists(char_audio):
            char_audio = paths["video"]

        char_transcription = self.transcriber.transcribe(char_audio)
        char_subs_raw = char_transcription.to_list()
        narr_transcription = (
            self.transcriber.transcribe(paths["narrator"])
            if os.path.exists(paths["narrator"])
            else None
        )
        narr_subs_raw = narr_transcription.to_list() if narr_transcription else []
        save_srt(char_subs_raw, os.path.join(project_dir, "character.srt"))
        save_srt(narr_subs_raw, os.path.join(project_dir, "narrator.srt"))

        # Load video and get dimensions
        video_clip = VideoFileClip(paths["video"])
        w, h = video_clip.size

        # Create nameplate clips via Overlay classes
        NAME_FSIZE = 50
        font_p = "assets/Minecraft.ttf"

        # Helper to get dimensions from a NameplateOverlay
        def get_nameplate_dims(text: str, fsize: int, color: str, font_path: str, stroke_w: int) -> tuple[int, int]:
            """Extract width and height from nameplate overlay rendering."""
            try:
                font = ImageFont.truetype(os.path.abspath(font_path), int(fsize))
            except:
                font = ImageFont.load_default()
            l, t, r, b = font.getbbox(text)
            tw, th = r - l, b - t
            sw = int(stroke_w)
            return tw + 2 * sw + 10, th + 2 * sw + 10

        tw_l, th_l = get_nameplate_dims(name_l, NAME_FSIZE, "white", font_p, 3)
        tw_r, th_r = get_nameplate_dims(name_r, NAME_FSIZE, "white", font_p, 3)

        lbl_l_overlay = NameplateOverlay(
            text=name_l, fontsize=NAME_FSIZE, color="white", duration=99,
            font_path=font_p, stroke_width=3, pos=(0, 0)
        )
        lbl_r_overlay = NameplateOverlay(
            text=name_r, fontsize=NAME_FSIZE, color="white", duration=99,
            font_path=font_p, stroke_width=3, pos=(0, 0)
        )

        # Calculate nameplate positions
        # (hl_x, hl_y, hr_x, hr_y already set from parameters)
        V_OFFSET = 60
        pos_l_x, pos_l_y = int(hl_x * w - tw_l / 2), int(hl_y * h - th_l - V_OFFSET)
        pos_r_x, pos_r_y = int(hr_x * w - tw_r / 2), int(hr_y * h - th_r - V_OFFSET)
        pos_l_x, pos_l_y = max(5, min(w - tw_l - 5, pos_l_x)), max(
            5, min(h - th_l - 5, pos_l_y)
        )
        pos_r_x, pos_r_y = max(5, min(w - tw_r - 5, pos_r_x)), max(
            5, min(h - th_r - 5, pos_r_y)
        )
        POS_L, POS_R = (pos_l_x, pos_l_y), (pos_r_x, pos_r_y)

        # Render nameplate clips from overlays
        lbl_l_exact = lbl_l_overlay.to_clip((w, h))
        lbl_r_exact = lbl_r_overlay.to_clip((w, h))

        # Prepare background images
        if os.path.exists(paths["image"]):
            img_orig_pil = (
                Image.open(paths["image"])
                .convert("RGB")
                .resize((w, h), Image.Resampling.LANCZOS)
            )
            base_img = ImageClip(np.array(img_orig_pil))
            img_for_blur = img_orig_pil.copy()
            draw = ImageDraw.Draw(img_for_blur)
            try:
                font_pix = ImageFont.truetype(
                    os.path.abspath(font_p), NAME_FSIZE
                )
            except:
                font_pix = ImageFont.load_default()
            draw.text(
                (pos_l_x + tw_l // 2, pos_l_y + th_l // 2),
                name_l,
                font=font_pix,
                fill="white",
                anchor="mm",
                stroke_width=3,
                stroke_fill="black",
            )
            draw.text(
                (pos_r_x + tw_r // 2, pos_r_y + th_r // 2),
                name_r,
                font=font_pix,
                fill="white",
                anchor="mm",
                stroke_width=3,
                stroke_fill="black",
            )
            blur_bg_with_names = ImageClip(
                np.array(img_for_blur.filter(ImageFilter.GaussianBlur(radius=25)))
            )
        else:
            base_img = ColorClip(size=(w, h), color=(50, 50, 50))
            blur_bg_with_names = ColorClip(size=(w, h), color=(30, 30, 30))

        lbl_l_pers = lbl_l_exact.with_position(POS_L)
        lbl_r_pers = lbl_r_exact.with_position(POS_R)

        # Build intro segment
        INTRO_DUR, EYE_DUR = 1.2, 0.8
        bar_top = ColorClip(size=(w, h // 2), color=(0, 0, 0)).with_duration(
            EYE_DUR
        ).with_position(lambda t: ("center", -(t / EYE_DUR) * (h // 2)))
        bar_bot = ColorClip(size=(w, h // 2), color=(0, 0, 0)).with_duration(
            EYE_DUR
        ).with_position(lambda t: ("center", (h // 2) + (t / EYE_DUR) * (h // 2)))
        intro_part = CompositeVideoClip(
            [
                base_img.with_duration(INTRO_DUR),
                lbl_l_pers.with_duration(INTRO_DUR),
                lbl_r_pers.with_duration(INTRO_DUR),
                bar_top,
                bar_bot,
            ],
            size=(w, h),
        )

        # Build video segment with character subtitles
        vid_dur = video_clip.duration
        char_subs = []
        for s in char_subs_raw:
            if s["start"] < vid_dur:
                subtitle_overlay = SubtitleOverlay(
                    text=s["text"].upper(),
                    fontsize=72,
                    duration=min(s["end"], vid_dur) - s["start"]
                )
                badge = subtitle_overlay.to_clip((w, h))
                char_subs.append(
                    badge.with_start(s["start"]).with_position(
                        ("center", 0.78 * h)
                    )
                )
        video_part = CompositeVideoClip(
            [
                video_clip,
                lbl_l_pers.with_duration(vid_dur),
                lbl_r_pers.with_duration(vid_dur),
                *char_subs,
            ],
            size=(w, h),
        )

        # Build narration and choice segments if narrator exists
        if os.path.exists(paths["narrator"]):
            narrator_audio = AudioFileClip(paths["narrator"])
            narr_dur = narrator_audio.duration
            # Plus de gel sur base_image : fond = DERNIÈRE FRAME de la vidéo intro
            # (continuité visuelle) zoomée doucement sous la narration.
            try:
                bg_narr_src = video_clip.to_ImageClip(t=max(0.0, vid_dur - 0.05))
            except Exception:
                bg_narr_src = base_img
            img_bg_narr = bg_narr_src.with_duration(narr_dur)
            img_bg_narr = img_bg_narr.with_effects(
                [Resize(lambda t: 1.0 + 0.15 * (t / narr_dur))]
            )
            img_bg_narr = img_bg_narr.with_position("center")

            narr_subs = []
            for s in narr_subs_raw:
                if s["start"] < narr_dur:
                    subtitle_overlay = SubtitleOverlay(
                        text=s["text"].upper(),
                        fontsize=72,
                        duration=min(s["end"], narr_dur) - s["start"]
                    )
                    badge = subtitle_overlay.to_clip((w, h))
                    narr_subs.append(
                        badge.with_start(s["start"]).with_position(
                            ("center", 0.78 * h)
                        )
                    )
            narration_part = CompositeVideoClip(
                [
                    img_bg_narr,
                    lbl_l_pers.with_duration(narr_dur),
                    lbl_r_pers.with_duration(narr_dur),
                    *narr_subs,
                ],
                size=(w, h),
            ).with_audio(narrator_audio)

            # Build choice segment with timer and gauge
            T_STEP = 0.7
            CHOICE_DUR = T_STEP * 3
            choice_bg = blur_bg_with_names.with_duration(CHOICE_DUR)
            timer_size = 230
            countdown = [
                TimerOverlay(label=label, fontsize=160, size=timer_size, duration=T_STEP)
                .to_clip((w, h))
                .with_start(i * T_STEP)
                .with_position(("center", "center"))
                for i, label in enumerate(["3", "2", "1"])
            ]
            gauge_overlay = GaugeOverlay(width=w, duration=CHOICE_DUR)
            dark_gauge = gauge_overlay.to_clip((w, h)).with_position(
                ("center", int(0.65 * h))
            )
            choice_audio_el = []
            if os.path.exists(paths["tick"]):
                for step in [0, T_STEP, 2 * T_STEP]:
                    choice_audio_el.append(AudioFileClip(paths["tick"]).with_start(step))
            if os.path.exists(paths["beep"]):
                choice_audio_el.append(
                    AudioFileClip(paths["beep"]).with_start(CHOICE_DUR)
                )
            choice_part = CompositeVideoClip(
                [choice_bg, dark_gauge, *countdown], size=(w, h)
            )
            if choice_audio_el:
                choice_part = choice_part.with_audio(CompositeAudioClip(choice_audio_el))

            final_video = concatenate_videoclips(
                [intro_part, video_part, narration_part, choice_part], method="compose"
            )
        else:
            final_video = concatenate_videoclips(
                [intro_part, video_part], method="compose"
            )

        # Write output video
        final_video.write_videofile(
            paths["output"],
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=os.path.join(project_dir, "temp-audio.m4a"),
            remove_temp=True,
        )
        video_clip.close()
        if "narrator_audio" in locals():
            narrator_audio.close()

        return paths["output"]
