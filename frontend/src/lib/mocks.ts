// In-memory mock backend, contract-conformant with the live U1 API. Used when
// VITE_USE_MOCKS=true for offline demos. Satisfies the same StudioApi shape as
// the real client in api.ts.

import type {
  AdventureScript,
  Asset,
  ArcScene,
  ArtDirectionResult,
  BeatEntry,
  BeatsResponse,
  Brief,
  BriefResult,
  BrickSpec,
  BuildSceneResult,
  ScenePlanResult,
  ScenesState,
  Turn,
  CostEstimate,
  CreateEditorDocumentBody,
  CreateEpisodeBody,
  DialogueResult,
  DistributionKit,
  DistributionResult,
  EditorDoc,
  EditorDocument,
  EditorDocumentSummary,
  Episode,
  FormField,
  GenerateScriptBody,
  GenerativeKind,
  LibraryItem,
  ModelForm,
  ModelSearchResult,
  Project,
  RenderClip,
  RenderModel,
  Round,
  Template,
  TemplateSummary,
  CreateTemplateBody,
  RolePrompt,
  PromptTemplate,
  PromptTemplateSummary,
  CreatePromptTemplateBody,
  Scene,
  SceneDocumentResult,
  Theme,
  UpdateAssetBody,
} from "./types"
import { isClipBrick, isGenerativeBrick, isTextBrick } from "./types"

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
    out.push({ round_index: r, beat: "character.voice", kind: "audio", image_prompt: null, motion_prompt: null, text: SCRIPT.rounds[r]?.character_line_fr ?? null })
    out.push({ round_index: r, beat: "narration", kind: "audio", image_prompt: null, motion_prompt: null, text: SCRIPT.rounds[r]?.action_narration_fr ?? null })
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
      },
      {
        id: "brk-voice-1", type: "voice", model_ref: "minimax/speech-2.8-turbo",
        params: { text: "Tu cours dans le noir, le souffle court.", voice_id: "male-conteur" },
        layers: [], placement: { track: 2, start: 0, duration: 4 },
      },
    ],
  }
}

// Document COMPOSITE (ClipBrick) — ce que produit le script IA, révisé en R2.
function newAdventureDoc(title: string): EditorDoc {
  const DUR = 4
  const clip = (id: string, start: number, kind: "video" | "photo", imgPrompt: string, motionPrompt: string, narr: string) => ({
    id,
    type: "clip" as const,
    kind,
    image: { model_ref: "bytedance/seedream-4.5", params: { prompt: imgPrompt, aspect_ratio: "9:16" } },
    motion: kind === "video"
      ? { model_ref: "prunaai/p-video", params: { prompt: motionPrompt, duration: DUR } }
      : null,
    children: [
      { id: `${id}__narr`, role: "narration" as const, model_ref: "minimax/speech-2.8-turbo", params: { text: narr, voice_id: "male-conteur" } },
    ],
    // Placement CHRONOLOGIQUE (plans séquentiels sur la piste principale).
    placement: { track: 0, start, duration: DUR },
  })
  return {
    schema_version: 2,
    title,
    canvas: { width: 1080, height: 1920, fps: 30 },
    global_context: { text: "Un court-métrage d'horreur vertical.", characters: {}, art_direction: "cinematic, cold tones", extra: {} },
    tracks: [{ index: 0, role: "main" }],
    bricks: [
      clip("c1", 0, "video", "an abandoned subway tunnel, dim flickering light", "slow forward dolly, static camera", "Tu cours dans le noir, le souffle court."),
      clip("c2", DUR, "photo", "a rusted metal door covered in scratches", "", "Une porte. Derrière, un souffle."),
      clip("c3", DUR * 2, "video", "a flooded boiler room, black water rising", "slow tilt up, static camera", "L'eau monte. Il faut choisir, vite."),
    ],
  }
}

let nextTemplateId = 1
const templates = new Map<string, Template>()

function seedTemplates() {
  if (templates.size) return
  const id = `tpl-${nextTemplateId++}`
  templates.set(id, {
    id,
    name: "POV horreur — 3 plans",
    slots: [
      { id: "s1", kind: "video", duration: 4, aspect_ratio: "9:16", resolution: "720p", narration: true },
      { id: "s2", kind: "photo", duration: 3, aspect_ratio: "9:16", resolution: "720p", narration: true },
      { id: "s3", kind: "video", duration: 5, aspect_ratio: "9:16", resolution: "720p", narration: true },
    ],
  })
}

// Trous {token} uniques (ordre d'apparition) — miroir de la dérivation serveur.
function holesOf(identity: string, roles: RolePrompt[]): string[] {
  const seen: string[] = []
  const scan = (t: string) => {
    for (const m of t.matchAll(/\{([a-zA-Z0-9_]+)\}/g)) {
      const tok = m[1]
      if (tok && !seen.includes(tok)) seen.push(tok)
    }
  }
  scan(identity)
  for (const r of roles) for (const v of Object.values(r.fields)) scan(v)
  return seen
}

let nextPromptId = 1
const promptTemplates = new Map<string, PromptTemplate>()

function seedPromptTemplates() {
  if (promptTemplates.size) return
  const id = `spt-${nextPromptId++}`
  const identity = "Style : court-métrage d'horreur POV, {ton}, caméra à l'épaule, cold tones."
  const roles: RolePrompt[] = [
    { id: "r1", label: "Accroche", fields: { decor: "On découvre {lieu}", sujet: "POV", camera: "à l'épaule", narration: "Une menace : {danger}." } },
    { id: "r2", label: "Tension", fields: { action: "{personnage} comprend qu'il faut fuir {danger}", camera: "travelling avant" } },
    { id: "r3", label: "Chute", fields: { action: "Issue face à {danger}", narration: "Survie ou mort." } },
  ]
  promptTemplates.set(id, { id, name: "POV horreur — identité", identity, roles, holes: holesOf(identity, roles) })
}

// Miroir du Fake backend : idée → scènes (photo d'env + 2 plans courts chacune).
function newSceneDoc(title: string, nScenes: number): EditorDoc {
  const bricks: EditorDoc["bricks"] = []
  const scenes: Scene[] = []
  let cursor = 0
  const push = (b: EditorDoc["bricks"][number], dur: number) => {
    bricks.push(b)
    cursor += dur
  }
  for (let i = 1; i <= Math.max(1, nScenes); i++) {
    const envId = `s${i}_env`
    push(
      {
        id: envId, type: "clip", kind: "photo",
        image: { model_ref: "bytedance/seedream-4.5", params: { prompt: `location ${i} exterior, cold ambient light` } },
        shot: { decor: `location ${i} exterior`, lumiere: "cold ambient light", cadrage: "", characters: [], extra: "" },
        children: [], layers: [], placement: { track: 0, start: cursor, duration: 3 },
      },
      3
    )
    const shotIds = [envId]
    const shots: [string, number, string, string, string, string][] = [
      ["sh1", 3, "slow push in, static camera", "La tension monte.", "close-up", "tense, looking around"],
      ["sh2", 4, "handheld, static framing", "Un choix s'impose.", "medium POV shot", "resolute, deciding"],
    ]
    for (const [k, dur, motion, narr, framing, play] of shots) {
      const sid = `s${i}_${k}`
      const [expr, act] = play.split(", ")
      const compiled = `${framing} of Léa (young woman, short dark hair), wearing worn grey coat, ${play}, in location ${i} interior, cold ambient light`
      push(
        {
          id: sid, type: "clip", kind: "video",
          image: { model_ref: "bytedance/seedream-4.5", params: { prompt: compiled } },
          motion: { model_ref: "prunaai/p-video", params: { prompt: motion, duration: dur, image: `{brick:${envId}.image}` } },
          shot: {
            decor: `location ${i} interior`, lumiere: "cold ambient light", cadrage: framing, extra: "",
            characters: [{ ref: "lea", name: "Léa", wardrobe: "", expression: expr ?? "", action: act ?? "" }],
          },
          children: [{ id: `${sid}__narr`, role: "narration", model_ref: "minimax/speech-2.8-turbo", params: { text: narr, voice_id: "male-conteur" } }],
          layers: [], placement: { track: 0, start: cursor, duration: dur },
        },
        dur
      )
      shotIds.push(sid)
    }
    scenes.push({
      id: `s${i}`, title: `Scène ${i}`,
      context: { text: `Le contexte concentré de la scène ${i}.`, characters: {}, art_direction: "cold tones", extra: {} },
      environment_photo_ref: envId, shot_ids: shotIds,
    })
  }
  return {
    schema_version: 4, title,
    canvas: { width: 1080, height: 1920, fps: 30 },
    global_context: { text: title, characters: {}, art_direction: "cold tones", extra: {} },
    tracks: [{ index: 0, role: "main" }], bricks, scenes,
    bible: [{ id: "lea", name: "Léa", appearance: "young woman, short dark hair", wardrobe: "worn grey coat", voice_id: "male-conteur", traits: "determined" }],
  }
}

let nextDocId = 1
const editorDocuments = new Map<string, EditorDocument>()
const episodeToDoc = new Map<number, string>()  // épisode → dernier doc de scènes
const distributionByDoc = new Map<string, DistributionKit>()  // doc → fiche de sortie
const briefByEpisode = new Map<number, Brief>()  // épisode → brief du producteur
// Table ronde (mock) : état de production par document (arc + scènes faites + débats).
const roomStateByDoc = new Map<
  string,
  { arc: ArcScene[]; built: string[]; transcripts: Record<string, Turn[]> }
>()

function cannedTurns(title: string, isNew: boolean): Turn[] {
  return [
    { role: "realisateur", message: `On ouvre sur « ${title} ». On garde le rythme et le ton.` },
    { role: "directeur_artistique", message: "Décor froid, lumière dure, textures marquées." },
    { role: "chef_operateur", message: "Un large d'accroche puis un plan serré. Caméra fixe." },
    { role: "casting", message: isNew ? "On introduit Léa : jeune femme, cheveux courts, manteau gris." : "Léa est présente, on garde sa continuité." },
    { role: "dialoguiste", message: "Narration courte, en français, une phrase qui installe." },
    { role: "realisateur", message: `OK, on verrouille « ${title} ».` },
    { role: "directeur_artistique", message: "On reste dans l'identité visuelle établie." },
    { role: "chef_operateur", message: "Deux plans d'environ 4 secondes." },
    { role: "casting", message: "Tenue par défaut, expression tendue." },
    { role: "dialoguiste", message: "« La tension monte. »" },
  ]
}

function appendMockScene(doc: EditorDoc, sceneId: string, title: string, isNew: boolean): void {
  if (isNew && !(doc.bible ?? []).some((c) => c.id === "lea")) {
    doc.bible = [
      ...(doc.bible ?? []),
      { id: "lea", name: "Léa", appearance: "young woman, short dark hair", wardrobe: "worn grey coat", voice_id: "male-conteur", traits: "déterminée" },
    ]
  }
  let cursor = doc.bricks.reduce((m, b) => Math.max(m, (b.placement?.start ?? 0) + (b.placement?.duration ?? 0)), 0)
  const envId = `${sceneId}_env`
  doc.bricks.push({
    id: envId, type: "clip", kind: "photo",
    image: { model_ref: "bytedance/seedream-4.5", params: { prompt: `establishing shot of ${title}, cold ambient light` } },
    shot: { decor: `establishing shot of ${title}`, lumiere: "cold ambient light", cadrage: "", characters: [], extra: "" },
    children: [], layers: [], placement: { track: 0, start: cursor, duration: 3 },
  })
  cursor += 3
  const shotIds = [envId]
  for (const [k, framing, expr] of [["sh1", "wide shot", "tense"], ["sh2", "close-up", "resolute"]] as const) {
    const sid = `${sceneId}_${k}`
    doc.bricks.push({
      id: sid, type: "clip", kind: "video",
      image: { model_ref: "bytedance/seedream-4.5", params: { prompt: `${framing} of Léa (young woman, short dark hair), wearing worn grey coat, ${expr}, in ${title}` } },
      motion: { model_ref: "prunaai/p-video", params: { prompt: "static camera", duration: 4, image: `{brick:${envId}.image}` } },
      shot: { decor: title, lumiere: "cold ambient light", cadrage: framing, extra: "", characters: [{ ref: "lea", name: "Léa", wardrobe: "", expression: expr, action: "in scene" }] },
      children: [{ id: `${sid}__narr`, role: "narration", model_ref: "minimax/speech-2.8-turbo", params: { text: "La tension monte.", voice_id: "male-conteur" } }],
      layers: [], placement: { track: 0, start: cursor, duration: 4 },
    })
    cursor += 4
    shotIds.push(sid)
  }
  doc.scenes = [
    ...(doc.scenes ?? []),
    { id: sceneId, title, context: { text: title, characters: {}, art_direction: "cold tones", extra: {} }, environment_photo_ref: envId, shot_ids: shotIds },
  ]
}

function seedEditorDocs() {
  if (editorDocuments.size) return
  const id = `doc-${nextDocId++}`
  editorDocuments.set(id, { id, project_id: 1, title: "Métro hanté — montage", doc: newEditorDoc("Métro hanté — montage") })
  const id2 = `doc-${nextDocId++}`
  editorDocuments.set(id2, { id: id2, project_id: 1, title: "Métro hanté — briques (revue)", doc: newAdventureDoc("Métro hanté — briques (revue)") })
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
      src = ("source_path" in b && b.source_path ? b.source_path : PLACEHOLDER_IMG)
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
    if (body.brief && e.id != null) briefByEpisode.set(e.id, structuredClone(body.brief))
    return e
  },
  async proposeBrief(body: { idea: string; partial?: Partial<Brief> }): Promise<BriefResult> {
    await delay(400)
    const pitch = body.idea.trim() || "une vidéo verticale"
    const proposed: Brief = {
      objectif: `Faire découvrir : ${pitch.slice(0, 120)}`,
      audience: "créateurs et curieux sur mobile (18-34)",
      plateforme: "tiktok",
      duree_s: 30,
      budget_usd: 0,
      ton: "dynamique et captivant",
      langue: "fr",
      notes: "",
    }
    // Le mock n'appelle jamais OpenAI → brief de démo (l'humain édite ensuite).
    return { ...proposed, ...(body.partial ?? {}), source: "fake" }
  },
  async getBrief(episodeId: number): Promise<Brief> {
    await delay()
    const b = briefByEpisode.get(episodeId)
    if (!b) throw new Error("aucun brief pour cet épisode")
    return structuredClone(b)
  },
  async saveBrief(episodeId: number, brief: Brief): Promise<Brief> {
    await delay(150)
    briefByEpisode.set(episodeId, structuredClone(brief))
    return structuredClone(brief)
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
  async planScenes(
    episodeId: number,
    body: { prompt: string; n_scenes?: number; title?: string }
  ): Promise<ScenePlanResult> {
    await delay(400)
    const id = `doc-${nextDocId++}`
    const beats = ["Accroche", "Montée", "Chute"]
    const n = body.n_scenes ?? 3
    const arc: ArcScene[] = Array.from({ length: Math.max(1, n) }, (_, i) => ({
      id: `s${i + 1}`,
      title: `Scène ${i + 1} — ${beats[i] ?? "Suite"}`,
    }))
    const doc: EditorDoc = {
      schema_version: 4, title: body.title || "Nouvelle vidéo",
      canvas: { width: 1080, height: 1920, fps: 30 },
      global_context: { text: body.prompt, characters: {}, art_direction: "cold tones", extra: {} },
      tracks: [{ index: 0, role: "main" }], bricks: [], scenes: [], bible: [],
    }
    editorDocuments.set(id, { id, project_id: 1, title: doc.title, doc })
    episodeToDoc.set(episodeId, id)
    roomStateByDoc.set(id, { arc, built: [], transcripts: {} })
    return { id, title: doc.title, doc: structuredClone(doc), arc, source: "fake" }
  },

  async buildNextScene(docId: string): Promise<BuildSceneResult> {
    await delay(600)
    const st = roomStateByDoc.get(docId)
    const docu = editorDocuments.get(docId)
    if (!st || !docu) throw new Error("aucune table ronde ouverte")
    const next = st.arc.find((s) => !st.built.includes(s.id))
    if (!next) throw new Error("toutes les scènes sont construites")
    const isNew = st.built.length === 0
    appendMockScene(docu.doc, next.id, next.title, isNew)
    const transcript = cannedTurns(next.title, isNew)
    st.built.push(next.id)
    st.transcripts[next.id] = transcript
    const remaining = st.arc.filter((s) => !st.built.includes(s.id)).map((s) => s.id)
    return {
      id: docId, scene_id: next.id, title: next.title, transcript, remaining,
      doc: structuredClone(docu.doc), source: "fake",
    }
  },

  async scenesState(docId: string): Promise<ScenesState> {
    await delay()
    const st = roomStateByDoc.get(docId)
    if (!st) return { arc: [], built: [], remaining: [] }
    return {
      arc: structuredClone(st.arc), built: [...st.built],
      remaining: st.arc.filter((s) => !st.built.includes(s.id)).map((s) => s.id),
    }
  },

  async sceneTranscript(docId: string, sceneId: string): Promise<{ scene_id: string; transcript: Turn[] }> {
    await delay()
    const st = roomStateByDoc.get(docId)
    const turns = st?.transcripts[sceneId]
    if (!turns) throw new Error("aucun débat pour cette scène")
    return { scene_id: sceneId, transcript: structuredClone(turns) }
  },

  async createSceneDocument(
    episodeId: number,
    body: { prompt: string; style_identity?: string; n_scenes?: number; title?: string }
  ): Promise<SceneDocumentResult> {
    await delay(400)
    const id = `doc-${nextDocId++}`
    const doc = newSceneDoc(body.title || "Nouvelle vidéo", body.n_scenes ?? 3)
    const docu: EditorDocument = { id, project_id: 1, title: doc.title, doc }
    editorDocuments.set(id, docu)
    episodeToDoc.set(episodeId, id)
    // Le mock n'appelle jamais OpenAI → scènes de démo.
    return { ...structuredClone(docu), source: "fake" }
  },

  async getEpisodeDocument(episodeId: number): Promise<EditorDocument> {
    await delay()
    const docId = episodeToDoc.get(episodeId)
    const d = docId ? editorDocuments.get(docId) : undefined
    if (!d) throw new Error("aucun document pour cet épisode")
    return structuredClone(d)
  },

  async reviewFromScript(episodeId: number): Promise<EditorDocument> {
    await delay()
    const id = `doc-${nextDocId++}`
    const docu: EditorDocument = {
      id, project_id: 1, title: `Épisode ${episodeId} — briques`,
      doc: newAdventureDoc(`Épisode ${episodeId} — briques`),
    }
    editorDocuments.set(id, docu)
    return structuredClone(docu)
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

  async directArtDirection(id: string): Promise<ArtDirectionResult> {
    await delay(400)
    const existing = editorDocuments.get(id)
    if (!existing) throw new Error("editor document not found")
    // Le mock n'appelle jamais OpenAI → direction de démo, mais MUTE réellement le
    // doc (comme le backend) : suffixe de style sur chaque photo d'environnement.
    const style = "cinematic, cohesive mood, consistent color grade, filmic texture"
    existing.doc.global_context.art_direction = style
    const byId = new Map(existing.doc.bricks.map((b) => [b.id, b]))
    for (const scene of existing.doc.scenes ?? []) {
      const env = byId.get(scene.environment_photo_ref)
      if (env && isClipBrick(env)) {
        const p = env.image.params.prompt
        const cur = (typeof p === "string" ? p : "").trim()
        env.image.params.prompt = `${cur} — art direction: ${style}`.trim()
      }
    }
    return { ...structuredClone(existing), source: "fake" }
  },

  async directDialogue(id: string): Promise<DialogueResult> {
    await delay(400)
    const existing = editorDocuments.get(id)
    if (!existing) throw new Error("editor document not found")
    // Le mock n'appelle jamais OpenAI → dialogue de démo, mais MUTE réellement le
    // doc : normalise chaque réplique (majuscule initiale + ponctuation finale).
    for (const b of existing.doc.bricks) {
      if (!isClipBrick(b)) continue
      for (const child of b.children) {
        const t = child.params.text
        const cur = (typeof t === "string" ? t : "").trim()
        if (!cur) continue
        const polished = cur[0]!.toUpperCase() + cur.slice(1)
        child.params.text = /[.!?…]$/.test(polished) ? polished : `${polished}.`
      }
    }
    return { ...structuredClone(existing), source: "fake" }
  },

  async listTemplates(): Promise<TemplateSummary[]> {
    await delay()
    seedTemplates()
    return [...templates.values()].map((t) => ({
      id: t.id,
      name: t.name,
      slot_count: t.slots.length,
      total_duration: t.slots.reduce((a, s) => a + s.duration, 0),
    }))
  },

  async createTemplate(body: CreateTemplateBody): Promise<Template> {
    await delay()
    const id = `tpl-${nextTemplateId++}`
    const t: Template = { id, name: body.name, slots: structuredClone(body.slots) }
    templates.set(id, t)
    return structuredClone(t)
  },

  async getTemplate(id: string): Promise<Template> {
    await delay()
    seedTemplates()
    const t = templates.get(id)
    if (!t) throw new Error("template not found")
    return structuredClone(t)
  },

  async saveTemplate(id: string, body: CreateTemplateBody): Promise<Template> {
    await delay(150)
    const t = templates.get(id)
    if (!t) throw new Error("template not found")
    t.name = body.name
    t.slots = structuredClone(body.slots)
    return structuredClone(t)
  },

  async deleteTemplate(id: string): Promise<{ ok: boolean }> {
    await delay()
    templates.delete(id)
    return { ok: true }
  },

  async listPromptTemplates(): Promise<PromptTemplateSummary[]> {
    await delay()
    seedPromptTemplates()
    return [...promptTemplates.values()].map((t) => ({
      id: t.id,
      name: t.name,
      role_count: t.roles.length,
      hole_count: holesOf(t.identity, t.roles).length,
    }))
  },

  async createPromptTemplate(body: CreatePromptTemplateBody): Promise<PromptTemplate> {
    await delay()
    const id = `spt-${nextPromptId++}`
    const t: PromptTemplate = {
      id,
      name: body.name,
      identity: body.identity,
      roles: structuredClone(body.roles),
      holes: holesOf(body.identity, body.roles),
    }
    promptTemplates.set(id, t)
    return structuredClone(t)
  },

  async getPromptTemplate(id: string): Promise<PromptTemplate> {
    await delay()
    seedPromptTemplates()
    const t = promptTemplates.get(id)
    if (!t) throw new Error("prompt template not found")
    return structuredClone(t)
  },

  async savePromptTemplate(id: string, body: CreatePromptTemplateBody): Promise<PromptTemplate> {
    await delay(150)
    const t = promptTemplates.get(id)
    if (!t) throw new Error("prompt template not found")
    t.name = body.name
    t.identity = body.identity
    t.roles = structuredClone(body.roles)
    t.holes = holesOf(body.identity, body.roles)
    return structuredClone(t)
  },

  async deletePromptTemplate(id: string): Promise<{ ok: boolean }> {
    await delay()
    promptTemplates.delete(id)
    return { ok: true }
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

  async getDistribution(id: string): Promise<DistributionResult> {
    await delay()
    const kit = distributionByDoc.get(id)
    if (!kit) throw new Error("aucune fiche de sortie pour ce document")
    return { id, ...structuredClone(kit) }
  },
  async generateDistribution(id: string): Promise<DistributionResult> {
    await delay(500)
    const doc = editorDocuments.get(id)
    const name = doc?.title || "Nouvelle vidéo"
    const kit: DistributionKit = {
      title: `${name} 😱 (tu ne vas pas y croire)`,
      description: `${name} — une vidéo verticale à regarder jusqu'au bout. Abonne-toi !`,
      hashtags: ["#fyp", "#pourtoi", "#story", "#viral", "#shorts"],
      hook: "Attends de voir la fin…",
    }
    distributionByDoc.set(id, kit)
    return { id, source: "fake", ...structuredClone(kit) }
  },
  async saveDistribution(id: string, kit: DistributionKit): Promise<DistributionResult> {
    await delay(150)
    distributionByDoc.set(id, structuredClone(kit))
    return { id, ...structuredClone(kit) }
  },

  async uploadFile(file: File) {
    await delay()
    return { ref: `mock-upload/${file.name}` }
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
