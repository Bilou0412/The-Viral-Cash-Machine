# Graph Report - The-Viral-Cash-Machine  (2026-06-09)

## Corpus Check
- 15 files · ~149,771 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 209 nodes · 219 edges · 17 communities (14 shown, 3 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `079174c7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Video Compilation & Subtitles|Video Compilation & Subtitles]]
- [[_COMMUNITY_App State & Instance Management|App State & Instance Management]]
- [[_COMMUNITY_AI Asset Generation|AI Asset Generation]]
- [[_COMMUNITY_Upscaling & Color Grading|Upscaling & Color Grading]]
- [[_COMMUNITY_OpenAI & Transcription|OpenAI & Transcription]]
- [[_COMMUNITY_Production Pipeline|Production Pipeline]]
- [[_COMMUNITY_Post-Processing Module|Post-Processing Module]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `metadata` - 32 edges
2. `compile_video_raw()` - 10 edges
3. `final_video` - 7 edges
4. `Refactor : procédural → feature-driven + ports (typing.Protocol)` - 7 edges
5. `Architecture` - 6 edges
6. `🇬🇧 English Version` - 6 edges
7. `Golden oracle — characterization tests` - 6 edges
8. `VideoInstance` - 5 edges
9. `key_frames` - 5 edges
10. `media_duration()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Instance-Based Generation` --references--> `VideoInstance`  [INFERRED]
  README.md → app.py
- `compile_video_raw()` --shares_data_with--> `VideoInstance`  [INFERRED]
  compiler.py → app.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **3-Step Production Pipeline Flow** — claude_step1_asset_generation, claude_step2_raw_compilation, claude_step3_ai_upscale [EXTRACTED 0.95]
- **Step 2 Compilation Subsystems** — compiler_compile_video_raw, claude_whisper, compiler_get_ai_head_positions_split, claude_moviepy [EXTRACTED 0.90]
- **Multi-AI Model Orchestration** — claude_prunaai_p_video, claude_seedream, claude_minimax_speech, claude_replicate_api [EXTRACTED 0.90]

## Communities (17 total, 3 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.06
Nodes (32): metadata, char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url (+24 more)

### Community 1 - "App State & Instance Management"
Cohesion: 0.15
Nodes (20): app.py (Streamlit UI), download_file(), get_whisper_subtitles(), load_into_editor(), log_terminal(), save_key_to_env(), sync_instance_to_widgets(), VideoInstance (+12 more)

### Community 2 - "AI Asset Generation"
Cohesion: 0.17
Nodes (10): 2-Step Production Pipeline, Architecture, Commands, Data Model, External Dependencies, graphify, Important Conventions, Key File Roles (+2 more)

### Community 3 - "Upscaling & Color Grading"
Cohesion: 0.06
Nodes (31): char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url, character_speech (+23 more)

### Community 4 - "OpenAI & Transcription"
Cohesion: 0.14
Nodes (13): 🇬🇧 English Version, ✨ Fonctionnalités Principales, 🚀 Installation & Configuration, 🚀 Installation & Setup, ✨ Key Features, 🛠️ Prerequisites, 📂 Project Structure / Structure du Projet, 🛠️ Prérequis (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (7): Contexte, Fichiers clés touchés, Refactor : procédural → feature-driven + ports (typing.Protocol), Règle de décision pour les Protocol (cadrée avec l'utilisateur), Structure cible (à la racine, `streamlit run app.py` inchangé), Séquencement strangler-fig (chaque étape = app fonctionnelle + mypy vert), Vérification

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (9): Building and Running, Configuration, Development Conventions, Prerequisites, Project Overview, Project Structure, Running the Application, Setup (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (16): extract_frame(), _ffprobe_value(), key_frame_timestamps(), media_duration(), _parse_fraction(), probe_to_dict(), probe_video(), Golden-oracle helpers for the strangler-fig refactor (ARCHITECTURE_PLAN.md, step (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.12
Nodes (17): file, sha256, timestamp, file, sha256, timestamp, file, sha256 (+9 more)

### Community 13 - "Community 13"
Cohesion: 0.18
Nodes (10): final_video, codec, duration, fps, height, nb_frames, width, metadata_sha256 (+2 more)

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (3): Characterization test against the frozen golden (ARCHITECTURE_PLAN.md, verificat, Re-extract each key frame from the frozen video and confirm its checksum., test_golden_key_frames_unchanged()

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (6): Golden oracle — characterization tests, Per-step workflow (steps 0 → 9), Running, Tooling, What is frozen — `fixtures/golden/`, Why

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (3): capture(), main(), Freeze a real production export as the golden oracle (ARCHITECTURE_PLAN.md, step

## Knowledge Gaps
- **126 isolated node(s):** `PreToolUse`, `allow`, `source_export`, `duration`, `width` (+121 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `metadata` connect `Video Compilation & Subtitles` to `Community 13`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `key_frames` connect `Community 12` to `Community 13`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `PreToolUse`, `allow`, `Freeze a real production export as the golden oracle (ARCHITECTURE_PLAN.md, step` to the rest of the system?**
  _134 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Video Compilation & Subtitles` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Should `App State & Instance Management` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._
- **Should `Upscaling & Color Grading` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Should `OpenAI & Transcription` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._