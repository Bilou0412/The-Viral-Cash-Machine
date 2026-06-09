# Graph Report - The-Viral-Cash-Machine  (2026-06-08)

## Corpus Check
- 9 files · ~8,499 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 80 nodes · 89 edges · 11 communities (8 shown, 3 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.9)
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

## God Nodes (most connected - your core abstractions)
1. `compile_video_raw()` - 10 edges
2. `Refactor : procédural → feature-driven + ports (typing.Protocol)` - 7 edges
3. `Architecture` - 6 edges
4. `🇬🇧 English Version` - 6 edges
5. `VideoInstance` - 5 edges
6. `ViralCashMachine_V2` - 5 edges
7. `Building and Running` - 5 edges
8. `🇫🇷 Version Française` - 5 edges
9. `log_terminal()` - 4 edges
10. `ai_upscale()` - 4 edges

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

## Communities (11 total, 3 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.33
Nodes (9): compile_video_raw(), create_circular_timer_pil(), create_dark_fantasy_gauge(), create_styled_subtitle_pil(), format_timestamp(), get_ai_head_positions_split(), get_whisper_subtitles(), _make_text_clip_exact() (+1 more)

### Community 1 - "App State & Instance Management"
Cohesion: 0.24
Nodes (11): app.py (Streamlit UI), download_file(), get_whisper_subtitles(), load_into_editor(), log_terminal(), save_key_to_env(), sync_instance_to_widgets(), VideoInstance (+3 more)

### Community 2 - "AI Asset Generation"
Cohesion: 0.17
Nodes (10): 3-Step Production Pipeline, Architecture, Commands, Data Model, External Dependencies, graphify, Important Conventions, Key File Roles (+2 more)

### Community 3 - "Upscaling & Color Grading"
Cohesion: 0.50
Nodes (4): ai_upscale(), color_grade_tiktok(), Upscale IA avec Real-ESRGAN (NCNN Vulkan) - Pipeline par images pour support vid, Color grading AMV Premium post-upscale IA.

### Community 4 - "OpenAI & Transcription"
Cohesion: 0.14
Nodes (13): 🇬🇧 English Version, ✨ Fonctionnalités Principales, 🚀 Installation & Configuration, 🚀 Installation & Setup, ✨ Key Features, 🛠️ Prerequisites, 📂 Project Structure / Structure du Projet, 🛠️ Prérequis (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (7): Contexte, Fichiers clés touchés, Refactor : procédural → feature-driven + ports (typing.Protocol), Règle de décision pour les Protocol (cadrée avec l'utilisateur), Structure cible (à la racine, `streamlit run app.py` inchangé), Séquencement strangler-fig (chaque étape = app fonctionnelle + mypy vert), Vérification

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (9): Building and Running, Configuration, Development Conventions, Prerequisites, Project Overview, Project Structure, Running the Application, Setup (+1 more)

## Knowledge Gaps
- **38 isolated node(s):** `PreToolUse`, `allow`, `Contexte`, `Règle de décision pour les Protocol (cadrée avec l'utilisateur)`, `Structure cible (à la racine, `streamlit run app.py` inchangé)` (+33 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VideoInstance` connect `App State & Instance Management` to `Video Compilation & Subtitles`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `compile_video_raw()` connect `Video Compilation & Subtitles` to `App State & Instance Management`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `VideoInstance` (e.g. with `compile_video_raw()` and `Instance-Based Generation`) actually correct?**
  _`VideoInstance` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `PreToolUse`, `allow`, `Upscale IA avec Real-ESRGAN (NCNN Vulkan) - Pipeline par images pour support vid` to the rest of the system?**
  _40 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `OpenAI & Transcription` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._