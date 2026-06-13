// Domain types mirroring the live U1 API contract (FastAPI). Verified against the
// running server's responses. Visual prompt fields are EN, dialogue/narration FR.

export type EpisodeStatus = "draft" | "assets" | "montage" | "done"

export type AssetType = "image" | "video" | "audio"

export type AssetStatus = "pending" | "generating" | "ready" | "failed" | "error"

// ── DB-backed resources ────────────────────────────────────────────────

export interface Project {
  id: number
  name: string
  created_at: string
  settings_json: string | null
}

export interface Episode {
  id: number
  project_id: number
  title: string
  status: EpisodeStatus
  format: string // "aventure"
  draft_mode: boolean
  duration_s: number | null
  final_path: string | null
  created_at: string
}

// ── AdventureScript (mirror of adventure.py) ───────────────────────────

export interface VoiceProfile {
  description: string // EN
}

export interface Choice {
  label_fr: string
  image_desc: string // EN
  is_fatal: boolean
}

export interface Round {
  action_desc: string
  action_narration_fr: string
  environment_desc: string
  danger_desc: string
  environment_narration_fr: string
  character_line_fr: string
  character_delivery: string
  choices: [Choice, Choice]
  choice_narration_fr: string
  fatal_kill_desc: string
  fatal_pov_reaction: string
  fatal_narration_fr: string
  survival_outcome_desc: string
  survival_narration_fr: string
}

export interface AdventureScript {
  char_left_name: string
  char_right_name: string
  char_left_desc: string
  char_right_desc: string
  char_left_voice: VoiceProfile
  char_right_voice: VoiceProfile
  transition_narration_fr: string
  rounds: [Round, Round, Round]
  epilogue_other_desc: string
  epilogue_narration_fr: string
}

// ── Beats (GET /episodes/{id}/beats) ───────────────────────────────────
// Flat list; the unique key is (round_index, beat). `beat` is a composite key
// like "action.frame" | "action.motion" | "choice.0" | "narration" |
// "character.voice" | "epilogue.frame". round_index is null for transition
// narration and the epilogue.

export interface BeatEntry {
  round_index: number | null
  beat: string
  kind: AssetType
  image_prompt: string | null
  motion_prompt: string | null
  text: string | null
}

export interface BeatsResponse {
  episode_id: number
  assets: BeatEntry[]
}

// ── Assets (GET /episodes/{id}/assets) ─────────────────────────────────

export interface Asset {
  id: number
  episode_id: number
  round_index: number | null
  beat: string
  kind: AssetType
  prompt: string
  local_path: string | null
  status: AssetStatus
  draft: boolean
  sha: string | null
  created_at: string
}

// ── Cost (GET /episodes/{id}/cost) ─────────────────────────────────────

export interface CostBreakdownRow {
  model: string
  units: number
  unit_kind: "image" | "second" | "kchar"
  amount_usd: number
}

export interface CostEstimate {
  episode_id: number
  estimated_usd: number
  actual_usd: number
  breakdown: CostBreakdownRow[]
}

// ── Library (GET /library) ─────────────────────────────────────────────

export interface LibraryItem {
  episode_id: number
  title: string
  project_id: number
  status: EpisodeStatus
  duration_s: number | null
  final_path: string | null
}

// ── SSE event payload (GET /events/{episode_id}) ───────────────────────

export type JobEventType =
  | "generation_started"
  | "asset_started"
  | "asset_ready"
  | "asset_failed"
  | "generation_done"

export interface JobEvent {
  type: JobEventType
  asset_id?: number
  beat?: string
  kind?: AssetType
  index?: number
  local_path?: string
  amount_usd?: number
  total?: number
}

// ── Request bodies ─────────────────────────────────────────────────────

export interface CreateEpisodeBody {
  project_id: number
  title: string
  draft_mode: boolean
}

export interface GenerateScriptBody {
  prompt: string
  char_left_name?: string
  char_right_name?: string
}
