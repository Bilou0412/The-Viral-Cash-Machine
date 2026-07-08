from src.features.compositing.compositor import RawVideoCompositor
from src.features.compositing.heads import GroundingDINOHeadDetector, HeadDetector
from src.features.transcription.ports import Transcriber
from src.features.transcription.whisper import WhisperTranscriber


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
