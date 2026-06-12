# Graph Report - The-Viral-Cash-Machine  (2026-06-12)

## Corpus Check
- 47 files · ~464,030 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 827 nodes · 1105 edges · 65 communities (55 shown, 10 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7dcb7a62`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Video Compilation & Subtitles|Video Compilation & Subtitles]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_AI Asset Generation|AI Asset Generation]]
- [[_COMMUNITY_Upscaling & Color Grading|Upscaling & Color Grading]]
- [[_COMMUNITY_OpenAI & Transcription|OpenAI & Transcription]]
- [[_COMMUNITY_Community 5|Community 5]]
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
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]

## God Nodes (most connected - your core abstractions)
1. `metadata` - 32 edges
2. `_Spec` - 22 edges
3. `$defs` - 19 edges
4. `RawVideoCompositor` - 18 edges
5. `legacy_spec()` - 17 edges
6. `VideoSpec` - 17 edges
7. `WhisperTranscriber` - 16 edges
8. `HeadDetector` - 15 edges
9. `BIBLE DE SÉRIE — *titre de travail : « La Coloc »*` - 14 edges
10. `GroundingDINOHeadDetector` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Transcriber` --uses--> `WhisperTranscriber`  [INFERRED]
  scripts/compiler.py → src/features/transcription/whisper.py
- `HeadDetector` --uses--> `WhisperTranscriber`  [INFERRED]
  scripts/compiler.py → src/features/transcription/whisper.py
- `test_json_round_trip()` --calls--> `legacy_spec()`  [EXTRACTED]
  tests/test_videospec.py → src/videospec/builder.py
- `test_legacy_spec_is_valid()` --calls--> `legacy_spec()`  [EXTRACTED]
  tests/test_videospec.py → src/videospec/builder.py
- `test_legacy_spec_without_narration()` --calls--> `legacy_spec()`  [EXTRACTED]
  tests/test_videospec.py → src/videospec/builder.py

## Import Cycles
- 1-file cycle: `src/features/transcription/whisper.py -> src/features/transcription/whisper.py`
- 1-file cycle: `src/features/scripting/openai_decomposer.py -> src/features/scripting/openai_decomposer.py`

## Hyperedges (group relationships)
- **3-Step Production Pipeline Flow** — claude_step1_asset_generation, claude_step2_raw_compilation, claude_step3_ai_upscale [EXTRACTED 0.95]
- **Step 2 Compilation Subsystems** — compiler_compile_video_raw, claude_whisper, compiler_get_ai_head_positions_split, claude_moviepy [EXTRACTED 0.90]
- **Multi-AI Model Orchestration** — claude_prunaai_p_video, claude_seedream, claude_minimax_speech, claude_replicate_api [EXTRACTED 0.90]

## Communities (65 total, 10 thin omitted)

### Community 0 - "Video Compilation & Subtitles"
Cohesion: 0.06
Nodes (32): metadata, char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url (+24 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (63): BaseModel, VideoSpec, VideoSpec, Tests du contrat VideoSpec : round-trip JSON, validation des refs, schéma., Critique pour le structured output : le LLM ne peut pas halluciner de champs., test_duplicate_asset_ids_rejected(), test_extra_fields_forbidden(), test_json_round_trip() (+55 more)

### Community 2 - "AI Asset Generation"
Cohesion: 0.15
Nodes (11): 2-Step Production Pipeline, Architecture, Commands, Data Model, External Dependencies, graphify, Important Conventions, Key File Roles (+3 more)

### Community 3 - "Upscaling & Color Grading"
Cohesion: 0.06
Nodes (31): char_left_gender, char_left_name, char_left_personality, char_right_gender, char_right_name, char_right_personality, character_audio_url, character_speech (+23 more)

### Community 4 - "OpenAI & Transcription"
Cohesion: 0.14
Nodes (13): 🇬🇧 English Version, ✨ Fonctionnalités Principales, 🚀 Installation & Configuration, 🚀 Installation & Setup, ✨ Key Features, 🛠️ Prerequisites, 📂 Project Structure / Structure du Projet, 🛠️ Prérequis (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (43): default, title, type, NameplateSpec, SubtitleStyle, TimerStyle, default, title (+35 more)

### Community 8 - "Community 8"
Cohesion: 0.20
Nodes (9): Contexte, Fichiers clés touchés, Phase IR — « la vidéo comme donnée » (studio génératif), Refactor : procédural → feature-driven + ports (typing.Protocol), Règle de décision pour les Protocol (cadrée avec l'utilisateur), Structure cible (à la racine, `streamlit run app.py` inchangé), Séquencement strangler-fig (chaque étape = app fonctionnelle + mypy vert), Vérification (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (36): additionalProperties, items, title, type, $ref, description, mapping, propertyName (+28 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (16): extract_frame(), _ffprobe_value(), key_frame_timestamps(), media_duration(), _parse_fraction(), probe_to_dict(), probe_video(), Golden-oracle helpers for the strangler-fig refactor (ARCHITECTURE_PLAN.md, step (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (27): file, sha256, timestamp, final_video, codec, duration, fps, height (+19 more)

### Community 13 - "Community 13"
Cohesion: 0.15
Nodes (17): AssetBundle, Pipeline, get_pipeline(), load_into_editor(), Get or create cached pipeline with injected dependencies., sync_instance_to_widgets(), VideoInstance, CompiledVideo (+9 more)

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
Cohesion: 0.17
Nodes (13): ScriptDecomposition, OpenAIScriptDecomposer, OpenAI GPT script decomposer implementation., Decomposes scripts using OpenAI GPT models., Initialize with OpenAI client and model.          Args:             client: Auth, Decompose script into visual elements.          Args:             script: User-p, Script decomposition ports., Port for decomposing user scripts into instance elements. (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (26): Video composition orchestration., Compose raw video from assets with immutable parameters.          Args:, GaugeOverlay, NameplateOverlay, Overlay, Port for video overlays (subtitles, timers, nameplates, etc.)., Character nameplate with position., Create nameplate clip. (+18 more)

### Community 23 - "Community 23"
Cohesion: 0.16
Nodes (17): Orchestrates video composition with injected dependencies., RawVideoCompositor, GroundingDINOHeadDetector, HeadDetector, HeadLayout, Head detection for character positioning., Detected head positions (normalized 0-1)., Port for detecting character head positions in an image. (+9 more)

### Community 28 - "Community 28"
Cohesion: 0.07
Nodes (32): action_sequence(), choice_image(), environment_showcase(), epilogue_other_path(), face_cam_dilemma(), fatal_outcome(), _join(), narrator_audition() (+24 more)

### Community 29 - "Community 29"
Cohesion: 0.20
Nodes (10): additionalProperties, description, properties, required, title, type, AbsolutePosition, x (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.14
Nodes (14): VoiceAsset, text, voice_id, title, type, default, title, type (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.05
Nodes (36): 10. Banque de refs *(À REMPLIR PAR L'AUTEUR — c'est TON carburant)*, 11. Direction artistique — LE MOCKUMENTAIRE VERTICAL ✅ *(validé : Community × The Office)*, 12. Identité des personnages (technique), 13. Les caricatures — fiches physiques canoniques, 1. Le concept en une phrase, 2. Les lois de la série, 3. La coloc (cast principal), 4. Le binôme central — Nabil × Sam *(relation réelle : l'auteur et Sefir, (+28 more)

### Community 32 - "Community 32"
Cohesion: 0.33
Nodes (6): IntroSegment, additionalProperties, description, required, title, type

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (10): AssetBundle, AssetProvider, Asset generation ports., Port for generating AI assets (voice, image, video)., Synthesize voice from text. Returns URL., Generate image from prompt. Returns URL., Generate animated video from image and prompt. Returns URL., Generated assets with URLs. (+2 more)

### Community 34 - "Community 34"
Cohesion: 0.33
Nodes (6): additionalProperties, description, required, title, type, CountdownSegment

### Community 35 - "Community 35"
Cohesion: 0.15
Nodes (16): HeadDetector, Protocol, OpenAI, Transcriber, Transcription, Cue, Complete transcription as immutable tuple of cues., Convert to list of dicts for backwards compat with metadata.json. (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (6): scale_from, scale_to, properties, zoom, anyOf, default

### Community 37 - "Community 37"
Cohesion: 0.05
Nodes (45): default, title, type, FileAsset, ImageAsset, VideoAsset, default, title (+37 more)

### Community 38 - "Community 38"
Cohesion: 0.25
Nodes (8): default, fps, height, width, y, anyOf, default, gauge

### Community 39 - "Community 39"
Cohesion: 0.22
Nodes (9): properties, default, title, type, fps, width, default, title (+1 more)

### Community 40 - "Community 40"
Cohesion: 0.29
Nodes (7): properties, subtitles, video, anyOf, default, title, type

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (9): properties, default, title, type, height, y, default, title (+1 more)

### Community 42 - "Community 42"
Cohesion: 0.18
Nodes (11): EyeOpenTransition, anyOf, default, title, type, additionalProperties, description, properties (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (6): FootageSegment, additionalProperties, description, required, title, type

### Community 44 - "Community 44"
Cohesion: 0.22
Nodes (6): AssetProvider, Synthesize voice using Minimax Speech model., Generate image using ByteDance SeedDream model., Generate animated video using Pruna P-Video model., Generate assets using Replicate AI models., ReplicateAssetProvider

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (6): NarrationSegment, additionalProperties, description, required, title, type

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (6): SubtitleTrack, additionalProperties, description, required, title, type

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (8): Acquis techniques des tests réels (ne pas re-découvrir), Doctrine voix (hybride — décision auteur), Format final de la vidéo (validé avec l'auteur), L'enjeu n°1 : les prompts (décision auteur — « optimiser un maximum sans diluer »), Plan d'extension — « L'Aventure » (format complet 3 rounds), Protocole par phase, Risques identifiés, État d'avancement — POINT DE REPRISE

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (9): scale_from, scale_to, default, title, type, default, title, type (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (6): $ref, default, items, title, type, nameplates

### Community 50 - "Community 50"
Cohesion: 0.50
Nodes (4): anyOf, default, title, end_sound

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (6): source, style, title, type, $ref, properties

### Community 52 - "Community 52"
Cohesion: 0.40
Nodes (5): additionalProperties, title, type, $defs, Canvas

### Community 53 - "Community 53"
Cohesion: 0.13
Nodes (15): HeadAnchor, additionalProperties, description, properties, required, title, type, side (+7 more)

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (5): type, const, default, title, type

### Community 55 - "Community 55"
Cohesion: 0.40
Nodes (6): font_path, fontsize, size, uppercase, default, default

### Community 56 - "Community 56"
Cohesion: 0.60
Nodes (3): download_file(), save_key_to_env(), log_terminal()

### Community 57 - "Community 57"
Cohesion: 0.40
Nodes (5): GaugeSpec, additionalProperties, description, title, type

### Community 58 - "Community 58"
Cohesion: 0.33
Nodes (6): type, steps, default, items, title, type

### Community 59 - "Community 59"
Cohesion: 0.25
Nodes (8): title, type, duration, properties, background, transition, anyOf, default

### Community 60 - "Community 60"
Cohesion: 0.40
Nodes (5): anyOf, default, title, type, audio

### Community 61 - "Community 61"
Cohesion: 0.40
Nodes (5): ZoomEffect, additionalProperties, description, title, type

### Community 62 - "Community 62"
Cohesion: 0.50
Nodes (4): default, title, type, blur_radius

### Community 64 - "Community 64"
Cohesion: 0.29
Nodes (7): properties, step_duration, timer, default, title, type, $ref

### Community 65 - "Community 65"
Cohesion: 0.50
Nodes (4): tick_sound, anyOf, default, title

## Knowledge Gaps
- **379 isolated node(s):** `Format final de la vidéo (validé avec l'auteur)`, `Doctrine voix (hybride — décision auteur)`, `L'enjeu n°1 : les prompts (décision auteur — « optimiser un maximum sans diluer »)`, `État d'avancement — POINT DE REPRISE`, `Protocole par phase` (+374 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `$defs` connect `Community 52` to `Community 32`, `Community 34`, `Community 37`, `Community 5`, `Community 9`, `Community 42`, `Community 43`, `Community 45`, `Community 46`, `Community 61`, `Community 53`, `Community 57`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `type` connect `Community 54` to `Community 64`, `Community 36`, `Community 37`, `Community 40`, `Community 53`, `Community 59`, `Community 29`, `Community 30`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Why does `properties` connect `Community 64` to `Community 65`, `Community 34`, `Community 38`, `Community 49`, `Community 50`, `Community 54`, `Community 58`, `Community 59`, `Community 62`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `RawVideoCompositor` (e.g. with `AssetBundle` and `AssetProvider`) actually correct?**
  _`RawVideoCompositor` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Bibliothèque de prompts — le composant n°1 du système.  Chaque type d'asset a so`, `Assemble les blocs non vides en un prompt compact.`, `Le perso face caméra pose son dilemme. Voix native, manière jouée.      voice_de` to the rest of the system?**
  _499 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Video Compilation & Subtitles` be split into smaller, more focused modules?**
  _Cohesion score 0.0625 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.0649452269170579 - nodes in this community are weakly interconnected._