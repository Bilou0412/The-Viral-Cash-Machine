// Shared presentation + factory helpers for bricks. Keeps the palette, timeline
// and inspector consistent on colors/labels and centralizes new-brick creation.

import type {
  Brick,
  BrickSpec,
  BrickType,
  GenerativeBrick,
  MediaBrick,
  Placement,
  TextBrick,
} from "@/lib/types"

export interface PaletteItem {
  type: BrickType
  label: string
  hint: string
  /** generative kind carries required_fields + preferred_models */
  spec?: BrickSpec
}

// Tailwind classes per brick type — accent on the timeline + palette chips.
export const BRICK_COLORS: Record<BrickType, { bg: string; border: string; text: string; dot: string }> = {
  image: { bg: "bg-sky-500/15", border: "border-sky-500/40", text: "text-sky-300", dot: "bg-sky-400" },
  video: { bg: "bg-violet-500/15", border: "border-violet-500/40", text: "text-violet-300", dot: "bg-violet-400" },
  voice: { bg: "bg-emerald-500/15", border: "border-emerald-500/40", text: "text-emerald-300", dot: "bg-emerald-400" },
  media: { bg: "bg-amber-500/15", border: "border-amber-500/40", text: "text-amber-300", dot: "bg-amber-400" },
  text: { bg: "bg-rose-500/15", border: "border-rose-500/40", text: "text-rose-300", dot: "bg-rose-400" },
  clip: { bg: "bg-primary/15", border: "border-primary/40", text: "text-primary", dot: "bg-primary" },
}

export const BRICK_LABELS: Record<BrickType, string> = {
  image: "Image",
  video: "Vidéo",
  voice: "Voix",
  media: "Média",
  text: "Texte",
  clip: "Brique",
}

// Non-generative bricks are hardcoded client-side (per the contract).
export const STATIC_PALETTE: PaletteItem[] = [
  { type: "media", label: "Média", hint: "Importer une vidéo / image" },
  { type: "text", label: "Texte", hint: "Sous-titre / cartouche" },
]

let counter = 0
function newId(type: BrickType) {
  counter += 1
  return `brk-${type}-${Date.now().toString(36)}-${counter}`
}

// Default placement: put it at the end of the relevant track.
function defaultPlacement(bricks: Brick[], track: number, duration: number): Placement {
  const onTrack = bricks.filter((b) => b.placement.track === track)
  const start = onTrack.reduce((acc, b) => Math.max(acc, b.placement.start + b.placement.duration), 0)
  return { track, start, duration }
}

const TRACK_FOR: Record<BrickType, number> = {
  image: 0, video: 0, media: 0, text: 1, voice: 2, clip: 0,
}

export function createBrick(item: PaletteItem, bricks: Brick[]): Brick {
  const track = TRACK_FOR[item.type]
  if (item.type === "text") {
    const placement = defaultPlacement(bricks, track, 3)
    const tb: TextBrick = { id: newId("text"), type: "text", payload: { text: "Nouveau texte" }, placement }
    return tb
  }
  if (item.type === "media") {
    const placement = defaultPlacement(bricks, track, 4)
    const mb: MediaBrick = { id: newId("media"), type: "media", layers: [], placement }
    return mb
  }
  // generative: image | video | voice (la palette ne crée jamais de "clip")
  const kind = item.type as GenerativeBrick["type"]
  const placement = defaultPlacement(bricks, track, 4)
  const model_ref = item.spec?.preferred_models[0] ?? ""
  const gb: GenerativeBrick = {
    id: newId(kind),
    type: kind,
    model_ref,
    params: {},
    layers: [],
    placement,
  }
  return gb
}

export const MIME = "application/x-vcm-brick"

// ── Brick connections (« brique → brique ») ───────────────────────────────
// A connection is encoded directly in a param value as the string
// "{brick:<id>}". The backend resolves it at generation time by substituting
// the referenced brick's generated output (topological order). Composing the
// timeline only mutates the draft; nothing generates.

const BRICK_REF_RE = /^\{brick:([^}]+)\}$/

/** If `value` is a "{brick:<id>}" connection string, return the id; else null. */
export function asBrickRef(value: unknown): string | null {
  if (typeof value !== "string") return null
  const m = BRICK_REF_RE.exec(value)
  return m ? m[1] : null
}

/** Encode a connection to a brick id as its param-value string. */
export function makeBrickRef(id: string): string {
  return `{brick:${id}}`
}

/** Field names that accept a media input even when their form type isn't "file". */
const MEDIA_INPUT_NAMES = new Set([
  "image",
  "image_input",
  "first_frame",
  "start_image",
  "init_image",
  "audio",
  "audio_input",
  "reference",
])

/** Whether a form field can be wired to another brick's output. */
export function isConnectableField(fieldName: string, fieldType: string): boolean {
  return fieldType === "file" || MEDIA_INPUT_NAMES.has(fieldName)
}

/** Only generative bricks (image/video/voice) and imported media produce outputs. */
export function isConnectableSource(b: Brick): boolean {
  return b.type !== "text"
}

/** Short, human-friendly id suffix for labels (e.g. "…a1b2"). */
function shortId(id: string): string {
  return id.length > 6 ? `#${id.slice(-4)}` : `#${id}`
}

/** Friendly label for a brick option in a connection dropdown / chip. */
export function brickRefLabel(b: Brick): string {
  const payloadTitle =
    "payload" in b && b.payload && typeof b.payload.title === "string"
      ? b.payload.title
      : undefined
  if (payloadTitle) return `${payloadTitle} ${shortId(b.id)}`
  if (b.type === "text") {
    const t = b.payload.text
    const txt = typeof t === "string" && t ? t : "Texte"
    return `${txt.slice(0, 24)} ${shortId(b.id)}`
  }
  if (b.type === "media") {
    return `${BRICK_LABELS.media} ${shortId(b.id)}`
  }
  if (b.type === "clip") {
    return `${BRICK_LABELS.clip} ${shortId(b.id)}`
  }
  const model = b.model_ref ? b.model_ref.split("/").pop() : BRICK_LABELS[b.type]
  return `${BRICK_LABELS[b.type]} · ${model} ${shortId(b.id)}`
}
