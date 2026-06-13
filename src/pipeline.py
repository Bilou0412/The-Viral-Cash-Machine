"""Feature-driven pipeline orchestration with immutable outputs."""

import os
from dataclasses import dataclass
from typing import Optional

from .features.transcription.ports import Transcriber
from .features.transcription.whisper import WhisperTranscriber
from .features.compositing.heads import HeadDetector, GroundingDINOHeadDetector, HeadLayout
from .features.compositing.compositor import RawVideoCompositor
from .features.assets.ports import AssetProvider, AssetBundle
from .features.assets.replicate_provider import ReplicateAssetProvider
from .infra.download import download_file


@dataclass(frozen=True)
class VideoInstance:
    """Immutable video instance with all composition parameters."""

    project_name: str
    instance_id: str
    char_left_name: str
    char_right_name: str
    head_l_x: float
    head_l_y: float
    head_r_x: float
    head_r_y: float


@dataclass(frozen=True)
class CompiledVideo:
    """Compiled video output."""

    output_path: str
    duration: float


class Pipeline:
    """Orchestrates feature-driven video generation with immutable outputs."""

    def __init__(
        self,
        asset_provider: Optional[AssetProvider] = None,
        transcriber: Optional[Transcriber] = None,
        head_detector: Optional[HeadDetector] = None,
    ):
        self.asset_provider = asset_provider or ReplicateAssetProvider()
        self.transcriber = transcriber or WhisperTranscriber()
        self.head_detector = head_detector or GroundingDINOHeadDetector()

    def generate_assets(
        self,
        project_name: str,
        instance_id: str,
        video_prompt: str,
        freeze_image_prompt: str,
        character_speech: str,
        narration_script: str,
        video_type: str = "intro",
    ) -> AssetBundle:
        """Generate all assets (voice, image, video). Returns immutable AssetBundle."""
        base = os.environ.get("VCM_OUTPUT_DIR", "exports")
        project_dir = os.path.join(base, project_name, instance_id)
        os.makedirs(project_dir, exist_ok=True)

        narrator_audio_url = None
        character_audio_url = None
        freeze_image_url = None
        video_url = None

        if narration_script:
            v_id = "Deep_Voice_Man" if video_type == "intro" else "Wise_Woman"
            narrator_audio_url = self.asset_provider.synthesize_voice(
                narration_script, v_id
            )

        if character_speech:
            character_audio_url = self.asset_provider.synthesize_voice(
                character_speech, "Deep_Voice_Man"
            )

        # Generate image
        # seedream-4.5 n'accepte que "2K", "4K" ou "custom"
        freeze_image_url = self.asset_provider.generate_image(
            freeze_image_prompt, "2K", "9:16"
        )

        # Animate video
        video_url = self.asset_provider.animate_video(
            video_prompt,
            freeze_image_url,
            duration=7,
            aspect_ratio="9:16",
            resolution="720p",  # p-video n'accepte que "720p"/"1080p"
            audio_url=character_audio_url,
            draft=False,
        )

        # Download and archive locally
        if narrator_audio_url:
            download_file(narrator_audio_url, project_dir, "narrator.mp3")
        if character_audio_url:
            download_file(character_audio_url, project_dir, "character.mp3")
        if freeze_image_url:
            download_file(freeze_image_url, project_dir, "base_image.png")
        if video_url:
            download_file(video_url, project_dir, "video.mp4")

        return AssetBundle(
            narrator_audio_url=narrator_audio_url,
            character_audio_url=character_audio_url,
            freeze_image_url=freeze_image_url,
            video_url=video_url,
        )

    def detect_heads(
        self, project_name: str, instance_id: str
    ) -> HeadLayout:
        """Detect character head positions. Returns immutable HeadLayout."""
        base = os.environ.get("VCM_OUTPUT_DIR", "exports")
        project_dir = os.path.join(base, project_name, instance_id)
        image_path = os.path.join(project_dir, "base_image.png")

        if not os.path.exists(image_path):
            # No image = use defaults
            return HeadLayout(left=(0.25, 0.40), right=(0.75, 0.40))

        return self.head_detector.detect(image_path, project_dir)

    def compile_video(self, video_instance: VideoInstance) -> CompiledVideo:
        """Compile final video from immutable instance parameters.

        Args:
            video_instance: Immutable VideoInstance with all composition parameters

        Returns:
            Immutable CompiledVideo with output path and duration
        """
        compositor = RawVideoCompositor(self.transcriber, self.head_detector)
        output_path = compositor.compose(
            video_instance.project_name,
            video_instance.instance_id,
            video_instance.char_left_name,
            video_instance.char_right_name,
            video_instance.head_l_x,
            video_instance.head_l_y,
            video_instance.head_r_x,
            video_instance.head_r_y,
        )

        # Get duration from output video
        try:
            from moviepy import VideoFileClip
            clip = VideoFileClip(output_path)
            duration = clip.duration
            clip.close()
        except:
            duration = 0.0

        return CompiledVideo(output_path=output_path, duration=duration)

    def produce(
        self,
        project_name: str,
        instance_id: str,
        char_left_name: str,
        char_right_name: str,
        video_prompt: str,
        freeze_image_prompt: str,
        character_speech: str,
        narration_script: str,
        video_type: str = "intro",
    ) -> tuple[AssetBundle, HeadLayout, CompiledVideo]:
        """Run full pipeline: assets → heads → compilation. Returns immutable outputs."""
        # Stage 1: Generate assets
        asset_bundle = self.generate_assets(
            project_name,
            instance_id,
            video_prompt,
            freeze_image_prompt,
            character_speech,
            narration_script,
            video_type,
        )

        # Stage 2: Detect heads
        head_layout = self.detect_heads(project_name, instance_id)

        # Stage 3: Compile video with immutable VideoInstance
        video_instance = VideoInstance(
            project_name=project_name,
            instance_id=instance_id,
            char_left_name=char_left_name,
            char_right_name=char_right_name,
            head_l_x=head_layout.left[0],
            head_l_y=head_layout.left[1],
            head_r_x=head_layout.right[0],
            head_r_y=head_layout.right[1],
        )
        compiled_video = self.compile_video(video_instance)

        return asset_bundle, head_layout, compiled_video
