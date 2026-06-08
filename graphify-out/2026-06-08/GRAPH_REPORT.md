# Graph Report - .  (2026-06-08)

## Corpus Check
- Corpus is ~6,259 words - fits in a single context window. You may not need a graph.

## Summary
- 47 nodes · 65 edges · 8 communities (6 shown, 2 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.82)
- Token cost: 22,000 input · 1,806 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Video Compilation & Subtitles|Video Compilation & Subtitles]]
- [[_COMMUNITY_App State & Instance Management|App State & Instance Management]]
- [[_COMMUNITY_AI Asset Generation|AI Asset Generation]]
- [[_COMMUNITY_Upscaling & Color Grading|Upscaling & Color Grading]]
- [[_COMMUNITY_OpenAI & Transcription|OpenAI & Transcription]]
- [[_COMMUNITY_Production Pipeline|Production Pipeline]]
- [[_COMMUNITY_Post-Processing Module|Post-Processing Module]]

## God Nodes (most connected - your core abstractions)
1. `compile_video_raw()` - 13 edges
2. `VideoInstance` - 6 edges
3. `ai_upscale()` - 6 edges
4. `Step 1 - Asset Generation` - 6 edges
5. `color_grade_tiktok()` - 5 edges
6. `app.py (Streamlit UI)` - 5 edges
7. `log_terminal()` - 4 edges
8. `get_ai_head_positions_split()` - 4 edges
9. `load_into_editor()` - 3 edges
10. `save_srt()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `get_ai_head_positions_split()` --semantically_similar_to--> `Whisper (word-level subtitles)`  [INFERRED] [semantically similar]
  compiler.py → CLAUDE.md
- `Instance-Based Generation` --references--> `VideoInstance`  [INFERRED]
  README.md → app.py
- `Step 2 - Raw Compilation` --implements--> `compile_video_raw()`  [EXTRACTED]
  CLAUDE.md → compiler.py
- `VideoInstance` --shares_data_with--> `metadata.json (serialized state)`  [EXTRACTED]
  app.py → CLAUDE.md
- `Step 3 - AI Upscale` --implements--> `ai_upscale()`  [EXTRACTED]
  CLAUDE.md → compiler.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **3-Step Production Pipeline Flow** — claude_step1_asset_generation, claude_step2_raw_compilation, claude_step3_ai_upscale [EXTRACTED 0.95]
- **Step 2 Compilation Subsystems** — compiler_compile_video_raw, claude_whisper, compiler_get_ai_head_positions_split, claude_moviepy [EXTRACTED 0.90]
- **Multi-AI Model Orchestration** — claude_prunaai_p_video, claude_seedream, claude_minimax_speech, claude_replicate_api [EXTRACTED 0.90]

## Communities (8 total, 2 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.31
Nodes (9): MoviePy, compile_video_raw(), create_circular_timer_pil(), create_dark_fantasy_gauge(), create_styled_subtitle_pil(), format_timestamp(), get_whisper_subtitles(), _make_text_clip_exact() (+1 more)

### Community 1 - "App State & Instance Management"
Cohesion: 0.31
Nodes (9): download_file(), get_whisper_subtitles(), load_into_editor(), log_terminal(), save_key_to_env(), sync_instance_to_widgets(), VideoInstance, metadata.json (serialized state) (+1 more)

### Community 2 - "AI Asset Generation"
Cohesion: 0.22
Nodes (9): Grounding DINO (head detection), minimax/speech-2.8-turbo (voice model), English-visual / French-dialogue convention, prunaai/p-video (video model), Replicate API, bytedance/seedream-4.5 (image model), Static camera prompt rule, Step 1 - Asset Generation (+1 more)

### Community 3 - "Upscaling & Color Grading"
Cohesion: 0.29
Nodes (7): FFmpeg, Real-ESRGAN (NCNN Vulkan), Step 3 - AI Upscale, ai_upscale(), color_grade_tiktok(), Upscale IA avec Real-ESRGAN (NCNN Vulkan) - Pipeline par images pour support vid, Color grading AMV Premium post-upscale IA.

### Community 4 - "OpenAI & Transcription"
Cohesion: 0.33
Nodes (6): app.py (Streamlit UI), OpenAI API, Step 2 - Raw Compilation, Whisper (word-level subtitles), log_terminal, save_key_to_env

## Knowledge Gaps
- **12 isolated node(s):** `3-Step Production Pipeline`, `Step 3 - AI Upscale`, `compiler.py (post-processing)`, `Real-ESRGAN (NCNN Vulkan)`, `FFmpeg` (+7 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VideoInstance` connect `App State & Instance Management` to `Video Compilation & Subtitles`, `OpenAI & Transcription`?**
  _High betweenness centrality (0.304) - this node is a cross-community bridge._
- **Why does `app.py (Streamlit UI)` connect `OpenAI & Transcription` to `App State & Instance Management`, `AI Asset Generation`?**
  _High betweenness centrality (0.267) - this node is a cross-community bridge._
- **Why does `compile_video_raw()` connect `Video Compilation & Subtitles` to `App State & Instance Management`, `AI Asset Generation`, `OpenAI & Transcription`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `VideoInstance` (e.g. with `compile_video_raw()` and `Instance-Based Generation`) actually correct?**
  _`VideoInstance` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Upscale IA avec Real-ESRGAN (NCNN Vulkan) - Pipeline par images pour support vid`, `Color grading AMV Premium post-upscale IA.`, `3-Step Production Pipeline` to the rest of the system?**
  _16 weakly-connected nodes found - possible documentation gaps or missing edges._