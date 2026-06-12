import os
from openai import OpenAI
from .ports import Cue, Transcription, Transcriber
from infra.logging import log_terminal


class WhisperTranscriber(Transcriber):
    """OpenAI Whisper-based speech-to-text with word-level timing."""

    def __init__(self, client: OpenAI | None = None):
        self.client = client

    def transcribe(self, audio_path: str) -> Transcription:
        """Transcribe audio using Whisper API with word-level granularity."""
        api_key = os.getenv("OPENAI_API_KEY")
        client = self.client or (OpenAI(api_key=api_key) if api_key else None)

        if not client or not os.path.exists(audio_path):
            return Transcription(cues=())

        try:
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                )

            cues_list: list[Cue] = []

            # Try word-level timing first
            if hasattr(transcript, "words") and transcript.words:
                raw_words = transcript.words
                for item in raw_words:
                    text_val = (
                        item.word if hasattr(item, "word") else getattr(item, "text", "")
                    )
                    if text_val:
                        cues_list.append(
                            Cue(
                                text=text_val.strip(),
                                start=item.start,
                                end=item.end,
                            )
                        )
            # Fall back to segment-level if word-level not available
            elif hasattr(transcript, "segments") and transcript.segments:
                for seg in transcript.segments:
                    words_in_seg = seg.text.strip().split()
                    if not words_in_seg:
                        continue
                    dur = seg.end - seg.start
                    word_dur = dur / len(words_in_seg)
                    for i, w in enumerate(words_in_seg):
                        cues_list.append(
                            Cue(
                                text=w.strip(),
                                start=seg.start + (i * word_dur),
                                end=seg.start + ((i + 1) * word_dur),
                            )
                        )

            return Transcription(cues=tuple(cues_list))
        except Exception as e:
            log_terminal("ERROR", f"Whisper failed for {audio_path}: {e}")
            return Transcription(cues=())
