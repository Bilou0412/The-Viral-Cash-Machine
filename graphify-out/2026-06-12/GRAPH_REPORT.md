# Graph Report - The-Viral-Cash-Machine  (2026-06-12)

## Corpus Check
- 36 files · ~152,001 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 384 nodes · 650 edges · 28 communities (18 shown, 10 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 134 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fe78803d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Video Compilation & Subtitles|Video Compilation & Subtitles]]
- [[_COMMUNITY_Community 1|Community 1]]
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
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]

## God Nodes (most connected - your core abstractions)
1. `metadata` - 32 edges
2. `RawVideoCompositor` - 29 edges
3. `WhisperTranscriber` - 29 edges
4. `HeadDetector` - 26 edges
5. `GroundingDINOHeadDetector` - 26 edges
6. `ReplicateAssetProvider` - 20 edges
7. `Pipeline` - 18 edges
8. `AssetProvider` - 17 edges
9. `VideoInstance` - 16 edges
10. `Transcriber` - 14 edges

## Surprising Connections (you probably didn't know these)
- `HeadDetector` --uses--> `HeadDetector`  [INFERRED]
  features/compositing/compositor.py → src/features/compositing/heads.py
- `Transcriber` --uses--> `HeadDetector`  [INFERRED]
  features/compositing/compositor.py → src/features/compositing/heads.py
- `Pipeline` --uses--> `Pipeline`  [INFERRED]
  app.py → pipeline.py
- `Pipeline` --uses--> `VideoInstance`  [INFERRED]
  app.py → pipeline.py
- `Transcriber` --uses--> `RawVideoCompositor`  [INFERRED]
  scripts/compiler.py → src/features/compositing/compositor.py

## Import Cycles
- 1-file cycle: `src/features/scripting/openai_decomposer.py -> src/features/scripting/openai_decomposer.py`
- 1-file cycle: `src/features/transcription/whisper.py -> src/features/transcription/whisper.py`
- 1-file cycle: `app.py -> app.py`

## Hyperedges (group relationships)
- **3-Step Production Pipeline Flow** — claude_step1_asset_generation, claude_step2_raw_compilation, claude_step3_ai_upscale [EXTRACTED 0.95]
- **Step 2 Compilation Subsystems** — compiler_compile_video_raw, claude_whisper, compiler_get_ai_head_positions_split, claude_moviepy [EXTRACTED 0.90]
- **Multi-AI Model Orchestration** — claude_prunaai_p_video, claude_seedream, claude_minimax_speech, claude_replicate_api [EXTRACTED 0.90]

## Communities (28 total, 10 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.06
Nodes (32): metadata, char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url (+24 more)

### Community 1 - "Community 1"
Cohesion: 0.22
Nodes (12): OpenAI, OpenAI, Transcription, Cue, Complete transcription as immutable tuple of cues., Convert to list of dicts for backwards compat with metadata.json., Port for speech-to-text services., Transcribe audio file and return cues with timing. (+4 more)

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
Cohesion: 0.50
Nodes (3): AssetProvider, HeadDetector, Transcriber

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (16): extract_frame(), _ffprobe_value(), key_frame_timestamps(), media_duration(), _parse_fraction(), probe_to_dict(), probe_video(), Golden-oracle helpers for the strangler-fig refactor (ARCHITECTURE_PLAN.md, step (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (27): file, sha256, timestamp, final_video, codec, duration, fps, height (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (24): get_pipeline(), load_into_editor(), Pipeline, Get or create cached pipeline with injected dependencies., sync_instance_to_widgets(), download_file(), save_key_to_env(), log_terminal() (+16 more)

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
Cohesion: 0.16
Nodes (14): OpenAI, ScriptDecomposition, OpenAIScriptDecomposer, OpenAI GPT script decomposer implementation., Decomposes scripts using OpenAI GPT models., Initialize with OpenAI client and model.          Args:             client: Auth, Decompose script into visual elements.          Args:             script: User-p, Script decomposition ports. (+6 more)

### Community 19 - "Community 19"
Cohesion: 0.10
Nodes (29): Video composition orchestration., Compose raw video from assets with immutable parameters.          Args:, GaugeOverlay, NameplateOverlay, Overlay, Port for video overlays (subtitles, timers, nameplates, etc.)., Character nameplate with position., Create nameplate clip. (+21 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (55): VideoInstance, AssetBundle, AssetProvider, AssetBundle, AssetProvider, Asset generation ports., Port for generating AI assets (voice, image, video)., Synthesize voice from text. Returns URL. (+47 more)

## Knowledge Gaps
- **120 isolated node(s):** `Project Overview`, `Commands`, `Ongoing refactor (resume point)`, `2-Step Production Pipeline`, `Data Model` (+115 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RawVideoCompositor` connect `Community 23` to `Community 19`, `Community 13`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `WhisperTranscriber` connect `Community 23` to `Community 9`, `Community 19`, `Community 13`, `Community 1`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `HeadDetector` connect `Community 23` to `Community 19`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `RawVideoCompositor` (e.g. with `AssetBundle` and `AssetProvider`) actually correct?**
  _`RawVideoCompositor` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `WhisperTranscriber` (e.g. with `VideoInstance` and `AssetBundle`) actually correct?**
  _`WhisperTranscriber` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `HeadDetector` (e.g. with `AssetBundle` and `HeadDetector`) actually correct?**
  _`HeadDetector` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `GroundingDINOHeadDetector` (e.g. with `VideoInstance` and `AssetBundle`) actually correct?**
  _`GroundingDINOHeadDetector` has 13 INFERRED edges - model-reasoned connections that need verification._