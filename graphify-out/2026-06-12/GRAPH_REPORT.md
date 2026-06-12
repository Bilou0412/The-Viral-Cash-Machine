# Graph Report - The-Viral-Cash-Machine  (2026-06-12)

## Corpus Check
- 32 files · ~152,498 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 336 nodes · 419 edges · 24 communities (17 shown, 7 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d4a2a411`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Video Compilation & Subtitles|Video Compilation & Subtitles]]
- [[_COMMUNITY_AI Asset Generation|AI Asset Generation]]
- [[_COMMUNITY_Upscaling & Color Grading|Upscaling & Color Grading]]
- [[_COMMUNITY_OpenAI & Transcription|OpenAI & Transcription]]
- [[_COMMUNITY_Production Pipeline|Production Pipeline]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]

## God Nodes (most connected - your core abstractions)
1. `metadata` - 32 edges
2. `compile_video_raw()` - 15 edges
3. `ImageClip` - 12 edges
4. `WhisperTranscriber` - 11 edges
5. `Pipeline` - 9 edges
6. `GroundingDINOHeadDetector` - 9 edges
7. `Transcriber` - 9 edges
8. `AssetProvider` - 8 edges
9. `ReplicateAssetProvider` - 8 edges
10. `RawVideoCompositor` - 8 edges

## Surprising Connections (you probably didn't know these)
- `VideoInstance` --uses--> `WhisperTranscriber`  [INFERRED]
  app.py → features/transcription/whisper.py
- `compile_video_raw()` --shares_data_with--> `VideoInstance`  [INFERRED]
  compiler.py → app.py
- `Transcriber` --uses--> `RawVideoCompositor`  [INFERRED]
  compiler.py → features/compositing/compositor.py
- `HeadDetector` --uses--> `RawVideoCompositor`  [INFERRED]
  compiler.py → features/compositing/compositor.py
- `VideoInstance` --uses--> `ReplicateAssetProvider`  [INFERRED]
  app.py → features/assets/replicate_provider.py

## Import Cycles
- 1-file cycle: `app.py -> app.py`
- 1-file cycle: `features/transcription/whisper.py -> features/transcription/whisper.py`

## Hyperedges (group relationships)
- **3-Step Production Pipeline Flow** — claude_step1_asset_generation, claude_step2_raw_compilation, claude_step3_ai_upscale [EXTRACTED 0.95]
- **Step 2 Compilation Subsystems** — compiler_compile_video_raw, claude_whisper, compiler_get_ai_head_positions_split, claude_moviepy [EXTRACTED 0.90]
- **Multi-AI Model Orchestration** — claude_prunaai_p_video, claude_seedream, claude_minimax_speech, claude_replicate_api [EXTRACTED 0.90]

## Communities (24 total, 7 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.06
Nodes (32): metadata, char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url (+24 more)

### Community 2 - "AI Asset Generation"
Cohesion: 0.15
Nodes (11): 2-Step Production Pipeline, Architecture, Commands, Data Model, External Dependencies, graphify, Important Conventions, Key File Roles (+3 more)

### Community 3 - "Upscaling & Color Grading"
Cohesion: 0.06
Nodes (31): char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url, character_speech (+23 more)

### Community 4 - "OpenAI & Transcription"
Cohesion: 0.14
Nodes (13): 🇬🇧 English Version, ✨ Fonctionnalités Principales, 🚀 Installation & Configuration, 🚀 Installation & Setup, ✨ Key Features, 🛠️ Prerequisites, 📂 Project Structure / Structure du Projet, 🛠️ Prérequis (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.22
Nodes (8): Contexte, Fichiers clés touchés, Refactor : procédural → feature-driven + ports (typing.Protocol), Règle de décision pour les Protocol (cadrée avec l'utilisateur), Structure cible (à la racine, `streamlit run app.py` inchangé), Séquencement strangler-fig (chaque étape = app fonctionnelle + mypy vert), Vérification, État d'avancement — POINT DE REPRISE

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (9): Building and Running, Configuration, Development Conventions, Prerequisites, Project Overview, Project Structure, Running the Application, Setup (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (16): extract_frame(), _ffprobe_value(), key_frame_timestamps(), media_duration(), _parse_fraction(), probe_to_dict(), probe_video(), Golden-oracle helpers for the strangler-fig refactor (ARCHITECTURE_PLAN.md, step (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (27): file, sha256, timestamp, final_video, codec, duration, fps, height (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (9): AssetBundle, AssetProvider, Asset generation ports., Port for generating AI assets (voice, image, video)., Synthesize voice from text. Returns URL., Generate image from prompt. Returns URL., Generate animated video from image and prompt. Returns URL., Generated assets with URLs. (+1 more)

### Community 14 - "Community 14"
Cohesion: 0.20
Nodes (3): Characterization test against the frozen golden (ARCHITECTURE_PLAN.md, verificat, Re-extract each key frame from the frozen video and confirm its checksum., test_golden_key_frames_unchanged()

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (6): Golden oracle — characterization tests, Per-step workflow (steps 0 → 9), Running, Tooling, What is frozen — `fixtures/golden/`, Why

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (3): capture(), main(), Freeze a real production export as the golden oracle (ARCHITECTURE_PLAN.md, step

### Community 18 - "Community 18"
Cohesion: 0.20
Nodes (13): OpenAI, Transcription, Cue, Complete transcription as immutable tuple of cues., Convert to list of dicts for backwards compat with metadata.json., Port for speech-to-text services., Transcribe audio file and return cues with timing., A single subtitle with timing. (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.06
Nodes (41): compile_video_raw(), create_circular_timer_pil(), create_dark_fantasy_gauge(), create_styled_subtitle_pil(), _make_text_clip_exact(), HeadDetector, Transcriber, Compile raw video from assets and metadata. (+33 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (31): get_pipeline(), load_into_editor(), Get or create cached pipeline with injected dependencies., sync_instance_to_widgets(), VideoInstance, AssetBundle, AssetProvider, Synthesize voice using Minimax Speech model. (+23 more)

### Community 24 - "Community 24"
Cohesion: 0.22
Nodes (7): HeadDetector, HeadLayout, Head detection for character positioning., Detected head positions (normalized 0-1)., Port for detecting character head positions in an image., Detect head positions and return normalized coordinates., Detect character heads using split-detection for parallel processing.

## Knowledge Gaps
- **129 isolated node(s):** `AssetProvider`, `Transcriber`, `HeadDetector`, `Transcriber`, `HeadDetector` (+124 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ReplicateAssetProvider` connect `Community 23` to `Community 13`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `compile_video_raw()` connect `Community 19` to `Community 18`, `Community 23`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `compile_video_raw()` (e.g. with `VideoInstance` and `ImageClip`) actually correct?**
  _`compile_video_raw()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ImageClip` (e.g. with `compile_video_raw()` and `create_circular_timer_pil()`) actually correct?**
  _`ImageClip` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WhisperTranscriber` (e.g. with `VideoInstance` and `Cue`) actually correct?**
  _`WhisperTranscriber` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Get or create cached pipeline with injected dependencies.`, `AssetProvider`, `Transcriber` to the rest of the system?**
  _192 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Video Compilation & Subtitles` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._