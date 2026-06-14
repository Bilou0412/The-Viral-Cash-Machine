// In-memory mock backend, contract-conformant with the live U1 API. Used when
// VITE_USE_MOCKS=true for offline demos. Satisfies the same StudioApi shape as
// the real client in api.ts.

import type {
  AdventureScript,
  Asset,
  BeatEntry,
  BeatsResponse,
  CostEstimate,
  CreateEpisodeBody,
  Episode,
  GenerateScriptBody,
  LibraryItem,
  Project,
  Round,
  Theme,
  UpdateAssetBody,
} from "./types"

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms))

function mkRound(env: string, danger: string): Round {
  return {
    action_desc: `running through ${env}`,
    action_narration_fr: "Tu cours, le souffle court, dans le noir.",
    environment_desc: env,
    danger_desc: danger,
    environment_narration_fr: "L'endroit pue la mort.",
    character_line_fr: "On ne peut pas rester ici...",
    character_delivery: "whispering, terrified",
    choices: [
      { label_fr: "Prendre l'escalier", image_desc: "a crumbling staircase", is_fatal: true },
      { label_fr: "Forcer la porte", image_desc: "a rusted iron door", is_fatal: false },
    ],
    choice_narration_fr: "L'escalier, ou la porte ?",
    fatal_kill_desc: `${danger} drags the victim into the dark`,
    fatal_pov_reaction: "hands flailing, screen shaking",
    fatal_narration_fr: "Si tu as choisi l'escalier... tu es déjà mort.",
    survival_outcome_desc: "barely escaping through the door",
    survival_narration_fr: "La porte cède. Tu respires encore.",
  }
}

const SCRIPT: AdventureScript = {
  char_left_name: "Étienne",
  char_right_name: "Marc",
  char_left_desc: "a pale young man with dark circles, torn jacket",
  char_right_desc: "a wiry scarred man with a cracked helmet lamp",
  char_left_voice: { description: "a trembling low male voice" },
  char_right_voice: { description: "a tense raspy male voice" },
  transition_narration_fr: "Si tu as choisi Étienne...",
  rounds: [
    mkRound("an abandoned subway tunnel", "a faceless crawling figure"),
    mkRound("a flooded boiler room", "rising black water"),
    mkRound("a collapsing rooftop", "a swarm of shadows"),
  ],
  epilogue_other_desc: "the other survivor reaching daylight",
  epilogue_narration_fr: "Si tu avais choisi l'autre... tu aurais vu le jour.",
}

const PLACEHOLDER_IMG =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='270' height='480'><rect width='100%' height='100%' fill='#111114'/><text x='50%' y='50%' fill='#e11d48' font-family='monospace' font-size='20' text-anchor='middle'>9:16</text></svg>`
  )

let nextId = 1000
const projects: Project[] = [
  { id: 1, name: "Horror Shorts FR", created_at: "2026-06-01T10:00:00Z", settings_json: null },
]
const themes: Theme[] = [{ name: "horror", label: "Horreur" }]
const episodes: Episode[] = [
  {
    id: 1, project_id: 1, title: "Le métro hanté", status: "done", format: "aventure",
    theme: "horror", draft_mode: false, duration_s: 58, final_path: "exports/x/final.mp4",
    created_at: "2026-06-02T10:00:00Z",
  },
  {
    id: 2, project_id: 1, title: "La chaufferie", status: "assets", format: "aventure",
    theme: "horror", draft_mode: true, duration_s: null, final_path: null,
    created_at: "2026-06-09T10:00:00Z",
  },
]
const scripts = new Map<number, AdventureScript>([[1, SCRIPT], [2, SCRIPT]])
const assetsByEpisode = new Map<number, Asset[]>()

const SHOTS = ["action", "environment", "character", "fatal", "survival"] as const

function buildBeatEntries(): BeatEntry[] {
  const out: BeatEntry[] = []
  for (let r = 0; r < 3; r++) {
    for (const s of SHOTS) {
      out.push({ round_index: r, beat: `${s}.frame`, kind: "image", image_prompt: `[frame] r${r + 1} ${s}`, motion_prompt: null, text: null })
      out.push({ round_index: r, beat: `${s}.motion`, kind: "video", image_prompt: `[frame] r${r + 1} ${s}`, motion_prompt: `[motion] r${r + 1} ${s}`, text: null })
    }
    out.push({ round_index: r, beat: "choice.0", kind: "image", image_prompt: `[choice A] r${r + 1}`, motion_prompt: null, text: null })
    out.push({ round_index: r, beat: "choice.1", kind: "image", image_prompt: `[choice B] r${r + 1}`, motion_prompt: null, text: null })
    out.push({ round_index: r, beat: "character.voice", kind: "audio", image_prompt: null, motion_prompt: null, text: SCRIPT.rounds[r].character_line_fr })
    out.push({ round_index: r, beat: "narration", kind: "audio", image_prompt: null, motion_prompt: null, text: SCRIPT.rounds[r].action_narration_fr })
  }
  out.push({ round_index: null, beat: "epilogue.frame", kind: "image", image_prompt: "[frame] epilogue", motion_prompt: null, text: null })
  out.push({ round_index: null, beat: "epilogue.motion", kind: "video", image_prompt: "[frame] epilogue", motion_prompt: "[motion] epilogue", text: null })
  out.push({ round_index: null, beat: "narration", kind: "audio", image_prompt: null, motion_prompt: null, text: SCRIPT.transition_narration_fr })
  return out
}

function seedAssets(episodeId: number): Asset[] {
  const now = new Date().toISOString()
  return buildBeatEntries().map((b) => ({
    id: nextId++, episode_id: episodeId, round_index: b.round_index, beat: b.beat,
    kind: b.kind, prompt: b.image_prompt ?? b.motion_prompt ?? b.text ?? "",
    local_path: b.kind === "image" ? "x.png" : b.kind === "video" ? "x.mp4" : "x.mp3",
    status: "ready", draft: true, excluded: false, sha: "abc123", created_at: now,
  }))
}

export const mockApi = {
  async listThemes() { await delay(); return [...themes] },

  async listProjects() { await delay(); return [...projects] },
  async createProject(name: string) {
    await delay()
    const p: Project = { id: nextId++, name, created_at: new Date().toISOString(), settings_json: null }
    projects.push(p)
    return p
  },
  async listEpisodes(projectId?: number) {
    await delay()
    return episodes.filter((e) => projectId == null || e.project_id === projectId)
  },
  async getEpisode(id: number) {
    await delay()
    const e = episodes.find((x) => x.id === id)
    if (!e) throw new Error("not found")
    return e
  },
  async createEpisode(body: CreateEpisodeBody) {
    await delay()
    const e: Episode = {
      id: nextId++, project_id: body.project_id, title: body.title, status: "draft",
      format: "aventure", theme: body.theme ?? "horror", draft_mode: body.draft_mode,
      duration_s: null, final_path: null, created_at: new Date().toISOString(),
    }
    episodes.push(e)
    return e
  },
  async generateScript(episodeId: number, body: GenerateScriptBody) {
    await delay(900)
    const s: AdventureScript = {
      ...SCRIPT,
      char_left_name: body.char_left_name || SCRIPT.char_left_name,
      char_right_name: body.char_right_name || SCRIPT.char_right_name,
    }
    scripts.set(episodeId, s)
    return s
  },
  async getScript(episodeId: number) {
    await delay()
    const s = scripts.get(episodeId)
    if (!s) throw new Error("not found")
    return s
  },
  async saveScript(episodeId: number, script: AdventureScript) {
    await delay()
    scripts.set(episodeId, script)
    return script
  },
  async getBeats(episodeId: number): Promise<BeatsResponse> {
    await delay()
    return { episode_id: episodeId, assets: buildBeatEntries() }
  },
  async getAssets(episodeId: number) {
    await delay()
    if (!assetsByEpisode.has(episodeId)) assetsByEpisode.set(episodeId, seedAssets(episodeId))
    return [...assetsByEpisode.get(episodeId)!]
  },
  async generateAssets(episodeId: number) {
    await delay(600)
    assetsByEpisode.set(episodeId, seedAssets(episodeId))
    const e = episodes.find((x) => x.id === episodeId)
    if (e) e.status = "assets"
    return { episode_id: episodeId, status: "scheduled" }
  },
  async regenerateAsset(assetId: number) {
    await delay(800)
    for (const list of assetsByEpisode.values()) {
      const a = list.find((x) => x.id === assetId)
      if (a) { a.created_at = new Date().toISOString(); break }
    }
    return { asset_id: assetId, status: "scheduled" }
  },
  async updateAsset(assetId: number, body: UpdateAssetBody): Promise<Asset> {
    await delay(300)
    for (const list of assetsByEpisode.values()) {
      const a = list.find((x) => x.id === assetId)
      if (a) {
        if (body.prompt !== undefined) a.prompt = body.prompt
        if (body.excluded !== undefined) a.excluded = body.excluded
        return { ...a }
      }
    }
    throw new Error("asset not found")
  },
  async getCost(episodeId: number): Promise<CostEstimate> {
    await delay()
    return {
      episode_id: episodeId, estimated_usd: 2.94, actual_usd: 0,
      breakdown: [
        { model: "bytedance/seedream-4.5", units: 22, unit_kind: "image", amount_usd: 0.66 },
        { model: "prunaai/p-video", units: 112, unit_kind: "second", amount_usd: 2.24 },
        { model: "minimax/speech-2.8-turbo", units: 1.977, unit_kind: "kchar", amount_usd: 0.0395 },
      ],
    }
  },
  async montage(episodeId: number) {
    await delay(1200)
    const e = episodes.find((x) => x.id === episodeId)!
    e.status = "done"; e.duration_s = 57; e.final_path = "exports/x/final.mp4"
    return { episode_id: episodeId, final_path: e.final_path }
  },
  async produce(episodeId: number) {
    await delay(400)
    return { episode_id: episodeId, status: "scheduled" }
  },
  async getLibrary(): Promise<LibraryItem[]> {
    await delay()
    return episodes
      .filter((e) => e.final_path)
      .map((e) => ({
        episode_id: e.id, title: e.title, project_id: e.project_id,
        status: e.status, duration_s: e.duration_s, final_path: e.final_path,
      }))
  },
}

// Re-export so callers building previews from mock assets get the placeholder.
export const MOCK_PLACEHOLDER_IMG = PLACEHOLDER_IMG
