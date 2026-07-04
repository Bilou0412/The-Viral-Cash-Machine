// In-memory mock backend, contract-conformant with the live U1 API. Used when
// VITE_USE_MOCKS=true for offline demos. Satisfies the same StudioApi shape as
// the real client in api.ts.

import type {
  AdventureScript,
  Asset,
  BeatEntry,
  BeatsResponse,
  BrickSpec,
  CostEstimate,
  CreateEditorDocumentBody,
  CreateEpisodeBody,
  EditorDoc,
  EditorDocument,
  EditorDocumentSummary,
  Episode,
  FormField,
  GenerateScriptBody,
  GenerativeBrick,
  GenerativeKind,
  LibraryItem,
  ModelForm,
  ModelSearchResult,
  Project,
  RenderClip,
  RenderModel,
  Round,
  Theme,
  UpdateAssetBody,
} from "./types"
import { isGenerativeBrick, isTextBrick } from "./types"

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

// ── Editor (E5) mocks ──────────────────────────────────────────────────

const BRICK_SPECS: BrickSpec[] = [
  {
    kind: "image",
    required_fields: ["prompt"],
    preferred_models: [
      "bytedance/seedream-4.5",
      "black-forest-labs/flux-1.1-pro",
      "google/imagen-4",
    ],
  },
  {
    kind: "video",
    required_fields: ["prompt", "image"],
    preferred_models: [
      "prunaai/p-video",
      "kwaivgi/kling-v2.1",
      "minimax/hailuo-02",
    ],
  },
  {
    kind: "voice",
    required_fields: ["text"],
    preferred_models: [
      "minimax/speech-2.8-turbo",
      "resemble-ai/chatterbox",
      "jaaari/kokoro-82m",
    ],
  },
]

// Per-model dynamic form. Keyed by model_ref; falls back to a generic schema.
function mockFormFields(modelRef: string): FormField[] {
  if (modelRef.includes("video") || modelRef.includes("kling") || modelRef.includes("hailuo")) {
    return [
      { name: "prompt", type: "string", required: true, default: "", enum: null, description: "Text prompt (EN).", order: 0, label: "Mouvement / action" },
      { name: "image", type: "file", required: true, default: null, enum: null, description: "First-frame image.", order: 1, label: "Image de départ", help: "Auto-liée à la photo de cette brique ; uploade une photo pour la remplacer." },
      { name: "duration", type: "integer", required: false, default: 5, enum: null, description: "Clip length (s).", order: 2, label: "Durée (s)" },
      { name: "aspect_ratio", type: "enum", required: false, default: "9:16", enum: ["9:16", "16:9", "1:1"], description: "Aspect ratio.", order: 3, label: "Format" },
      { name: "loop", type: "boolean", required: false, default: false, enum: null, description: "Loop the motion.", order: 4, label: "Boucle" },
    ]
  }
  if (modelRef.includes("speech") || modelRef.includes("chatterbox") || modelRef.includes("kokoro")) {
    return [
      { name: "text", type: "string", required: true, default: "", enum: null, description: "Text to speak (FR).", order: 0, label: "Texte à dire" },
      { name: "voice_id", type: "string", required: false, default: "male-conteur", enum: null, description: "Voice reference id.", order: 1, label: "Voix" },
      { name: "speed", type: "number", required: false, default: 1.0, enum: null, description: "Speech rate.", order: 2, label: "Vitesse" },
      { name: "emotion", type: "enum", required: false, default: "neutral", enum: ["neutral", "fearful", "tense", "calm"], description: "Delivery.", order: 3, label: "Émotion" },
    ]
  }
  // image
  return [
    { name: "prompt", type: "string", required: true, default: "", enum: null, description: "Text prompt (EN).", order: 0, label: "Description de l'image" },
    { name: "aspect_ratio", type: "enum", required: false, default: "9:16", enum: ["9:16", "16:9", "1:1", "4:3"], description: "Aspect ratio.", order: 1, label: "Format" },
    { name: "guidance", type: "number", required: false, default: 3.5, enum: null, description: "Prompt adherence.", order: 2, label: "Guidance" },
    { name: "seed", type: "integer", required: false, default: 0, enum: null, description: "Random seed (0 = random).", order: 3, label: "Seed" },
  ]
}

const MODEL_CATALOG: ModelSearchResult[] = [
  { owner: "bytedance", name: "seedream-4.5", cover: null, description: "Photoreal image gen, strong at 9:16." },
  { owner: "black-forest-labs", name: "flux-1.1-pro", cover: null, description: "High-fidelity image model." },
  { owner: "google", name: "imagen-4", cover: null, description: "Google Imagen 4 text-to-image." },
  { owner: "stability-ai", name: "sdxl", cover: null, description: "Open SDXL base." },
  { owner: "prunaai", name: "p-video", cover: null, description: "Fast image-to-video animation." },
  { owner: "kwaivgi", name: "kling-v2.1", cover: null, description: "Cinematic image-to-video." },
  { owner: "minimax", name: "hailuo-02", cover: null, description: "Image-to-video with strong motion." },
  { owner: "minimax", name: "speech-2.8-turbo", cover: null, description: "Multilingual TTS, voice cloning." },
  { owner: "resemble-ai", name: "chatterbox", cover: null, description: "Expressive TTS." },
  { owner: "jaaari", name: "kokoro-82m", cover: null, description: "Lightweight local-style TTS." },
]

function newEditorDoc(title: string): EditorDoc {
  return {
    schema_version: 1,
    title,
    canvas: { width: 1080, height: 1920, fps: 30 },
    global_context: {
      text: "Un court-métrage d'horreur vertical.",
      characters: { Conteur: "a deep, calm male narrator voice" },
      art_direction: "cinematic, high contrast, cold tones, film grain",
      extra: {},
    },
    tracks: [
      { index: 0, role: "main" },
      { index: 1, role: "overlay" },
      { index: 2, role: "audio" },
    ],
    bricks: [
      {
        id: "brk-img-1", type: "image", model_ref: "bytedance/seedream-4.5",
        params: { prompt: "an abandoned subway tunnel, dim flickering light", aspect_ratio: "9:16" },
        layers: [], placement: { track: 0, start: 0, duration: 4 },
      } as GenerativeBrick,
      {
        id: "brk-voice-1", type: "voice", model_ref: "minimax/speech-2.8-turbo",
        params: { text: "Tu cours dans le noir, le souffle court.", voice_id: "male-conteur" },
        layers: [], placement: { track: 2, start: 0, duration: 4 },
      } as GenerativeBrick,
    ],
  }
}

let nextDocId = 1
const editorDocuments = new Map<string, EditorDocument>()

function seedEditorDocs() {
  if (editorDocuments.size) return
  const id = `doc-${nextDocId++}`
  editorDocuments.set(id, { id, project_id: 1, title: "Métro hanté — montage", doc: newEditorDoc("Métro hanté — montage") })
}

// Derive a RenderModel from a doc's bricks (mirrors backend derivation).
function deriveRenderModel(doc: EditorDoc): RenderModel {
  const clips: RenderClip[] = []
  let total = 0
  for (const b of doc.bricks) {
    const { start, duration, track } = b.placement
    total = Math.max(total, start + duration)
    let media: RenderClip["media"]
    let text: string | undefined
    let src: string | null
    if (isGenerativeBrick(b)) {
      if (b.type === "video") { media = "video"; src = PLACEHOLDER_IMG }
      else if (b.type === "voice") { media = "audio"; src = null }
      else { media = "image"; src = PLACEHOLDER_IMG }
    } else if (isTextBrick(b)) {
      media = "text"
      src = null
      text = typeof b.payload.text === "string" ? b.payload.text : ""
    } else {
      media = "video"
      src = b.source_path ?? PLACEHOLDER_IMG
    }
    clips.push({ id: b.id, media, src, start, duration, track, z: 0, text })
  }
  return { version: "1.0", canvas: doc.canvas, clips, total_duration: total }
}

// In-memory BYOK key status for mock/e2e mode (no backend). Configurées par
// défaut → la démo/e2e ne montre pas la bannière « ajoute tes clés ».
const mockKeys = { openai_set: true, replicate_set: true }

// Mode mock/e2e : toujours authentifié en admin (le SPA ne redirige pas vers
// /login, la génération reste démontrable). Garde les tests Playwright verts.
const mockUser = { id: 1, email: "demo@vcm.local", is_admin: true }

export const mockApi = {
  async getMe() { await delay(); return { ...mockUser } },
  async login(_email: string, _password: string) { await delay(); return { ...mockUser } },
  async register(_email: string, _password: string) { await delay(); return { ...mockUser } },
  async logout() { await delay(); return { ok: true } },

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

  // ── Editor (E5) ──────────────────────────────────────────────────────
  async listBricks(): Promise<BrickSpec[]> { await delay(); return BRICK_SPECS.map((b) => ({ ...b })) },

  async getModelForm(owner: string, name: string): Promise<ModelForm> {
    await delay()
    const ref = `${owner}/${name}`
    return { model_ref: ref, version_id: `mock-${name}-v1`, fields: mockFormFields(ref) }
  },

  async searchModels(kind: GenerativeKind, q: string): Promise<ModelSearchResult[]> {
    await delay()
    const wantImage = kind === "image"
    const wantVideo = kind === "video"
    const wantVoice = kind === "voice"
    const term = q.trim().toLowerCase()
    return MODEL_CATALOG.filter((m) => {
      const ref = `${m.owner}/${m.name}`
      const isVideo = /video|kling|hailuo/.test(ref)
      const isVoice = /speech|chatterbox|kokoro/.test(ref)
      const isImage = !isVideo && !isVoice
      const kindOk = (wantImage && isImage) || (wantVideo && isVideo) || (wantVoice && isVoice)
      if (!kindOk) return false
      if (!term) return true
      return ref.includes(term) || m.description.toLowerCase().includes(term)
    }).map((m) => ({ ...m }))
  },

  async listEditorDocuments(projectId: number): Promise<EditorDocumentSummary[]> {
    await delay()
    seedEditorDocs()
    return [...editorDocuments.values()]
      .filter((d) => d.project_id === projectId)
      .map((d) => ({ id: d.id, project_id: d.project_id, title: d.title }))
  },

  async createEditorDocument(body: CreateEditorDocumentBody): Promise<EditorDocument> {
    await delay()
    const id = `doc-${nextDocId++}`
    const docu: EditorDocument = { id, project_id: body.project_id, title: body.title, doc: newEditorDoc(body.title) }
    editorDocuments.set(id, docu)
    return structuredClone(docu)
  },

  async getEditorDocument(id: string): Promise<EditorDocument> {
    await delay()
    seedEditorDocs()
    const d = editorDocuments.get(id)
    if (!d) throw new Error("editor document not found")
    return structuredClone(d)
  },

  async saveEditorDocument(id: string, doc: EditorDoc): Promise<EditorDocument> {
    await delay(150)
    const existing = editorDocuments.get(id)
    if (!existing) throw new Error("editor document not found")
    existing.doc = structuredClone(doc)
    existing.title = doc.title
    return structuredClone(existing)
  },

  async generateEditorDocument(id: string) {
    await delay(400)
    return { id, status: "scheduled" }
  },

  async regenerateBrick(id: string, brickId: string) {
    await delay(400)
    return { id, brick_id: brickId, status: "scheduled" }
  },

  async getRenderModel(id: string): Promise<RenderModel> {
    await delay()
    const d = editorDocuments.get(id)
    if (!d) throw new Error("editor document not found")
    return deriveRenderModel(d.doc)
  },

  async renderEditorDocument(id: string) {
    await delay(400)
    return { id, status: "scheduled" }
  },

  async getKeysStatus() {
    await delay()
    return { ...mockKeys }
  },

  async saveKeys(body: { openai?: string; replicate?: string }) {
    await delay()
    if (body.openai) mockKeys.openai_set = true
    if (body.replicate) mockKeys.replicate_set = true
    return { ...mockKeys }
  },
}

// Re-export so callers building previews from mock assets get the placeholder.
export const MOCK_PLACEHOLDER_IMG = PLACEHOLDER_IMG
