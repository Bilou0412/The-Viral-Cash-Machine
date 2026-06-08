# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ViralCashMachine V2 is a Streamlit dashboard that automates AI-powered vertical video (9:16) generation for TikTok/Shorts/Reels. It orchestrates multiple AI services (OpenAI, Replicate) to produce horror-themed short videos with character dialogues, narration, and interactive choices.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python -m streamlit run app.py

# Generate audio assets (tick/beep sound effects)
python generate_assets.py
```

On Windows, use `setup.bat` and `start.bat` instead.

## Architecture

### 3-Step Production Pipeline

The core workflow is a 3-step pipeline, each triggered by a button in the Streamlit UI:

1. **Step 1 - Asset Generation** (`app.py`): Calls Replicate APIs to generate voice audio (`minimax/speech-2.8-turbo`), base image (`bytedance/seedream-4.5`), and video animation (`prunaai/p-video`). Downloads all assets to `exports/{project}/{instance_id}/`.

2. **Step 2 - Raw Compilation** (`compiler.py:compile_video_raw`): Assembles the final video using MoviePy. This step:
   - Runs Whisper (OpenAI) for word-level subtitle extraction
   - Uses Grounding DINO (Replicate) via `get_ai_head_positions_split()` to detect character head positions for nameplate placement — splits the image into left/right halves and runs detection in parallel
   - Builds a multi-segment video: cinematic intro → video hook with subtitles → narration with zoom → countdown timer with choices
   - Output: `final_video.mp4`

3. **Step 3 - AI Upscale** (`compiler.py:ai_upscale`): Extracts frames, upscales with Real-ESRGAN (NCNN Vulkan, binary at `bin/realesrgan/`), reassembles. Optional `color_grade_tiktok()` applies AMV-style FFmpeg color grading. Output: `tiktok_final.mp4`

### Data Model

`VideoInstance` (dataclass in `app.py`) holds all state for one video unit: script, character config, AI-generated prompts, asset URLs, subtitle data, and head detection coordinates. Serialized as `metadata.json` in each instance directory.

### Key File Roles

- **`app.py`** — Streamlit UI, session state management, OpenAI prompt decomposition, Replicate API calls for asset generation
- **`compiler.py`** — All post-processing: MoviePy video assembly, Whisper subtitles, AI head detection, Real-ESRGAN upscaling, FFmpeg color grading
- **`generate_assets.py`** — One-off script to create `assets/tick.wav` and `assets/final.wav` sound effects

### External Dependencies

- **Replicate API** (`REPLICATE_API_TOKEN`): video gen, image gen, voice synthesis, Grounding DINO detection
- **OpenAI API** (`OPENAI_API_KEY`): script decomposition (GPT), Whisper transcription
- **Real-ESRGAN**: Windows binary expected at `bin/realesrgan/realesrgan-ncnn-vulkan.exe`
- **FFmpeg**: Required by MoviePy and color grading pipeline

### Storage Layout

```
exports/{project_name}/{instance_id}/
├── video.mp4          # Raw AI-generated video
├── base_image.png     # AI-generated freeze frame
├── character.mp3      # Character voice audio
├── narrator.mp3       # Narrator voice audio
├── metadata.json      # Serialized VideoInstance
├── final_video.mp4    # Step 2 output (compiled)
└── tiktok_final.mp4   # Step 3 output (upscaled)
```

## Important Conventions

- All visual prompts must be in English; dialogue/narration is in French
- Character names are French human names (never placeholders like "Monster A")
- Video prompts enforce strict static camera rules to prevent AI model drift
- The `compile_video_raw` function is the most complex piece — it handles intro animation, subtitle overlay, cinematic zoom, nameplate positioning, and countdown timer assembly in one pass
- Session state keys use short abbreviations (e.g., `inst_v_p`, `c_l_n`) to sync between widgets and the `VideoInstance` dataclass

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
