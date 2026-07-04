"""Freeze a real production export as the golden oracle (ARCHITECTURE_PLAN.md, step -1).

Run ONCE, before any refactor, against a directory produced by a real run:

    python tests/capture_golden.py exports/default_project/20260609_183531

It copies the durable artifacts into tests/fixtures/golden/ and records diffable
invariants (duration, segment plan, key-frame checksums, full metadata.json) in
invariants.json. Steps 0-9 then diff freshly produced videos against this point.

We freeze an *existing* export rather than re-running, so the golden costs no API
calls and is genuinely the pre-refactor reference.

The pipeline is Step 1 (assets) -> Step 2 (compilation); final_video.mp4 is the
final deliverable, so it is the single video the golden tracks.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden_tools as gt

GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "golden")


def capture(src_dir: str) -> dict:
    final_video = os.path.join(src_dir, "final_video.mp4")
    metadata = os.path.join(src_dir, "metadata.json")
    video = os.path.join(src_dir, "video.mp4")
    narrator = os.path.join(src_dir, "narrator.mp3")

    for required in (final_video, metadata, video):
        if not os.path.exists(required):
            raise FileNotFoundError(f"source export missing {required}")

    frames_dir = os.path.join(GOLDEN_DIR, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    shutil.copy2(final_video, os.path.join(GOLDEN_DIR, "final_video.mp4"))
    shutil.copy2(metadata, os.path.join(GOLDEN_DIR, "metadata.json"))

    plan = gt.segment_plan(video, narrator)
    timestamps = gt.key_frame_timestamps(plan)
    golden_final = os.path.join(GOLDEN_DIR, "final_video.mp4")

    frames = {}
    for name, ts in timestamps.items():
        png = os.path.join(frames_dir, f"{name}.png")
        gt.extract_frame(golden_final, ts, png)
        frames[name] = {"timestamp": ts, "sha256": gt.sha256_file(png),
                        "file": os.path.relpath(png, GOLDEN_DIR)}

    invariants = {
        "source_export": src_dir,
        "final_video": gt.probe_to_dict(gt.probe_video(golden_final)),
        "segment_plan": plan,
        "key_frames": frames,
        "metadata_sha256": gt.sha256_file(metadata),
        "metadata": gt.load_json(metadata),
    }
    with open(os.path.join(GOLDEN_DIR, "invariants.json"), "w", encoding="utf-8") as f:
        json.dump(invariants, f, indent=2, ensure_ascii=False)
    return invariants


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python tests/capture_golden.py <export_instance_dir>")
    inv = capture(sys.argv[1])
    print(f"frozen golden -> {GOLDEN_DIR}")
    print(f"  duration   : {inv['final_video']['duration']}s")
    print(f"  segments   : {len(inv['segment_plan'])} ({', '.join(s['name'] for s in inv['segment_plan'])})")
    print(f"  key frames : {', '.join(inv['key_frames'])}")


if __name__ == "__main__":
    main()
