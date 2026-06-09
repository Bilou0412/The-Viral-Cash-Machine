# Golden oracle — characterization tests

This directory is **step −1** of `ARCHITECTURE_PLAN.md`: the fixed reference frozen
*before* the feature-driven refactor, so every later step (0 → 9) can prove it did not
change the rendered output.

## Why

`compile_video_raw` is a god node the refactor takes apart piece by piece. Without a
frozen reference, "diff against the golden" (plan verification #2) has no fixed point.
So we froze one real, pre-refactor render and recorded diffable invariants from it.

The pipeline is **Step 1 (assets) → Step 2 (compilation)**; `final_video.mp4` is the
final deliverable, so it is the single video the oracle tracks. (The former Step 3 AI
upscale was removed from the project — there is no `tiktok_final.mp4`.)

## What is frozen — `fixtures/golden/`

| file | meaning |
|---|---|
| `final_video.mp4` | the reference render (Step 2 output) |
| `metadata.json` | the `VideoInstance` it was produced from |
| `frames/{intro,hook,narration,choice}.png` | one key frame per segment |
| `invariants.json` | duration, segment plan, key-frame checksums, full metadata |

Source: `exports/default_project/20260609_183531` — a real Docker run from before the
refactor (frozen, not re-generated, so zero API cost and a genuine pre-refactor point).

## Tooling

- `golden_tools.py` — ffprobe/ffmpeg + stdlib helpers (probe, segment plan, key-frame
  checksums, SSIM, stable-metadata diff). **No moviepy / numpy / PIL / GPU / network.**
- `capture_golden.py` — one-shot freezer. Re-run only to deliberately re-baseline:
  `python tests/capture_golden.py <export_instance_dir>`
- `test_golden.py` — the characterization test (below).

## Running

```bash
pip install -r requirements-dev.txt    # pytest; ffmpeg must be on PATH

# self-integrity only (the frozen golden still matches its recorded invariants)
pytest tests/test_golden.py

# regression check: diff a freshly produced render against the golden
GOLDEN_CANDIDATE=exports/<project>/<new_instance_id> pytest tests/test_golden.py
```

The candidate checks compare structure (codec/resolution/fps — exact), duration +
segment plan (tolerance `±0.20s`), visual fidelity (`SSIM ≥ 0.95`) and the stable
`metadata.json` keys (exact; volatile remote URLs and recomputed Whisper subtitles are
ignored — see `VOLATILE_META_KEYS`). Without `GOLDEN_CANDIDATE` those checks skip.

## Per-step workflow (steps 0 → 9)

1. Do the step. 2. `streamlit run app.py`, produce a video end-to-end (Step 1 → 2).
3. `GOLDEN_CANDIDATE=<that export> pytest tests/test_golden.py`. 4. Green → commit.
Any drift is a regression to explain before continuing.
