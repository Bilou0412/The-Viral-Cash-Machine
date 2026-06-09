"""Golden-oracle helpers for the strangler-fig refactor (ARCHITECTURE_PLAN.md, step -1).

Pure stdlib + ffmpeg/ffprobe on PATH. No moviepy / PIL / numpy, so this runs even
when the production deps are not installed and re-running the pipeline is impossible.

The oracle answers one question for steps 0-9: "does a freshly produced video still
match the reference frozen before any refactor?" Comparison is intentionally layered:

  * structure  - codec / resolution / fps  (must match exactly)
  * duration   - total + per-segment plan  (tolerance, encoders jitter the last frame)
  * visual     - SSIM of candidate vs golden (tolerance; survives benign re-encode noise)
  * metadata   - schema keys + head coords  (volatile fields like URLs are ignored)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, asdict

# --- segment model ---------------------------------------------------------
# compile_video_raw (compiler.py:298) concatenates these in this fixed order
# when a narrator track exists. INTRO_DUR / CHOICE_DUR are hard-coded constants;
# the two middle segments inherit the source media durations.
INTRO_DUR = 1.2          # compiler.py:354
T_STEP = 0.7             # compiler.py:381
CHOICE_DUR = T_STEP * 3  # compiler.py:382  -> 2.1s

# Names line up with the "frames-clés (intro / hook / narration / choice)" of the plan.
SEGMENT_NAMES = ("intro", "hook", "narration", "choice")


@dataclass(frozen=True)
class VideoProbe:
    duration: float
    width: int
    height: int
    fps: float
    codec: str
    nb_frames: int


def _run(cmd: list[str]) -> str:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {res.stderr.strip()}")
    return res.stdout.strip()


def _ffprobe_value(path: str, entries: str, stream: str | None = None) -> str:
    cmd = ["ffprobe", "-v", "error"]
    if stream is not None:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entries, "-of", "default=noprint_wrappers=1:nokey=1", path]
    return _run(cmd)


def media_duration(path: str) -> float:
    """Container duration in seconds (works for mp4, mp3, wav)."""
    return float(_ffprobe_value(path, "format=duration"))


def _parse_fraction(text: str) -> float:
    if "/" in text:
        num, den = text.split("/", 1)
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    return float(text)


def probe_video(path: str) -> VideoProbe:
    raw = _ffprobe_value(
        path,
        "stream=width,height,avg_frame_rate,codec_name,nb_frames",
        stream="v:0",
    ).splitlines()
    codec, width, height, fps_raw, nb_frames = raw
    return VideoProbe(
        duration=media_duration(path),
        width=int(width),
        height=int(height),
        fps=_parse_fraction(fps_raw),
        codec=codec,
        nb_frames=int(nb_frames),
    )


def segment_plan(video_path: str, narrator_path: str | None) -> list[dict]:
    """Reconstruct the concatenation plan that compile_video_raw produced.

    Mirrors compiler.py:394-396: 4 segments with a narrator, 2 without.
    Returns one dict per segment with name, duration and absolute [start,end].
    """
    vid_dur = media_duration(video_path)
    durations = [("intro", INTRO_DUR), ("hook", vid_dur)]
    if narrator_path and os.path.exists(narrator_path):
        durations += [("narration", media_duration(narrator_path)), ("choice", CHOICE_DUR)]

    plan, cursor = [], 0.0
    for name, dur in durations:
        plan.append({"name": name, "duration": round(dur, 3),
                     "start": round(cursor, 3), "end": round(cursor + dur, 3)})
        cursor += dur
    return plan


def key_frame_timestamps(plan: list[dict]) -> dict[str, float]:
    """Mid-point of each segment - the representative 'frame-clé' for that beat."""
    return {seg["name"]: round((seg["start"] + seg["end"]) / 2, 3) for seg in plan}


def extract_frame(video_path: str, timestamp: float, out_png: str) -> str:
    _run(["ffmpeg", "-v", "error", "-y", "-ss", f"{timestamp:.3f}",
          "-i", video_path, "-frames:v", "1", out_png])
    return out_png


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def ssim(candidate: str, reference: str) -> float:
    """Mean SSIM of candidate vs reference via ffmpeg's ssim filter (no python deps).

    Returns the 'All' average in [0,1]. 1.0 == identical.
    """
    # ssim writes its summary at info level, so we must NOT use -v error here.
    out = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", candidate, "-i", reference,
         "-lavfi", "ssim", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # ffmpeg prints e.g. "SSIM ... All:0.987654 (18.2)" on stderr
    for token in out.stderr.replace("\n", " ").split():
        if token.startswith("All:"):
            return float(token.split(":", 1)[1])
    raise RuntimeError(f"could not parse SSIM from ffmpeg output:\n{out.stderr}")


def probe_to_dict(p: VideoProbe) -> dict:
    return asdict(p)


# --- metadata.json comparison ---------------------------------------------
# Fields that legitimately change run-to-run (remote URLs) or are recomputed each
# compile (Whisper output). The refactor must not alter the *rest* of the schema.
VOLATILE_META_KEYS = frozenset({
    "video_url", "character_audio_url", "freeze_image_url", "narrator_audio_url",
    "character_subtitles", "narrator_subtitles",
})


def stable_metadata(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if k not in VOLATILE_META_KEYS}


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
