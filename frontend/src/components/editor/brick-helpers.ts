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
}

export const BRICK_LABELS: Record<BrickType, string> = {
  image: "Image",
  video: "Vidéo",
  voice: "Voix",
  media: "Média",
  text: "Texte",
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
  image: 0, video: 0, media: 0, text: 1, voice: 2,
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
  // generative: image | video | voice
  const placement = defaultPlacement(bricks, track, item.type === "voice" ? 4 : 4)
  const model_ref = item.spec?.preferred_models[0] ?? ""
  const gb: GenerativeBrick = {
    id: newId(item.type),
    type: item.type,
    model_ref,
    params: {},
    layers: [],
    placement,
  }
  return gb
}

export const MIME = "application/x-vcm-brick"
