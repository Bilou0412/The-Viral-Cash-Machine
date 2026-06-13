// Helpers to turn the API's flat beat/asset lists (composite `beat` keys like
// "action.frame", "action.motion", "choice.0", "narration", "character.voice")
// into the per-shot grouped view the Assets gallery renders.

import type { Asset, BeatEntry } from "./types"

export interface DisplayBeat {
  key: string // stable: `${round_index}:${group}` e.g. "0:action", "-1:epilogue"
  roundIndex: number | null
  group: string // "action" | "environment" | "character" | "fatal" | "survival" | "choice.0" | "choice.1" | "epilogue" | "narration"
  label: string
  framePrompt: string | null
  motionPrompt: string | null
  text: string | null
  image?: Asset
  video?: Asset
  audio?: Asset
}

const GROUP_LABELS: Record<string, string> = {
  action: "Action",
  environment: "Environnement",
  character: "Réplique",
  fatal: "Issue fatale",
  survival: "Survie",
  epilogue: "Épilogue",
  narration: "Narration",
  "choice.0": "Choix A",
  "choice.1": "Choix B",
}

const GROUP_ORDER = [
  "action",
  "environment",
  "character",
  "choice.0",
  "choice.1",
  "fatal",
  "survival",
  "narration",
  "epilogue",
]

/** "action.frame" -> "action"; "choice.0" -> "choice.0"; "narration" -> "narration". */
export function beatGroup(beat: string): string {
  if (beat.startsWith("choice.")) return beat
  const dot = beat.indexOf(".")
  return dot === -1 ? beat : beat.slice(0, dot)
}

function displayKey(roundIndex: number | null, group: string): string {
  return `${roundIndex ?? -1}:${group}`
}

/** Round index used for tab grouping: epilogue/transition (null) → -1. */
export function roundBucket(roundIndex: number | null): number {
  return roundIndex ?? -1
}

/** Merge beat prompts + generated assets into ordered DisplayBeat groups. */
export function buildDisplayBeats(beats: BeatEntry[], assets: Asset[]): DisplayBeat[] {
  const map = new Map<string, DisplayBeat>()

  const ensure = (roundIndex: number | null, group: string): DisplayBeat => {
    const key = displayKey(roundIndex, group)
    let db = map.get(key)
    if (!db) {
      db = {
        key,
        roundIndex,
        group,
        label: GROUP_LABELS[group] ?? group,
        framePrompt: null,
        motionPrompt: null,
        text: null,
      }
      map.set(key, db)
    }
    return db
  }

  for (const b of beats) {
    const db = ensure(b.round_index, beatGroup(b.beat))
    if (b.image_prompt && !db.framePrompt) db.framePrompt = b.image_prompt
    if (b.motion_prompt && !db.motionPrompt) db.motionPrompt = b.motion_prompt
    if (b.text && !db.text) db.text = b.text
  }

  for (const a of assets) {
    const db = ensure(a.round_index, beatGroup(a.beat))
    db[a.kind] = a
  }

  return [...map.values()].sort((x, y) => {
    const r = roundBucket(x.roundIndex) - roundBucket(y.roundIndex)
    if (r !== 0) return r
    return GROUP_ORDER.indexOf(x.group) - GROUP_ORDER.indexOf(y.group)
  })
}

/** Group display beats by round bucket for the per-round tabs. */
export function groupByRound(beats: DisplayBeat[]): [number, DisplayBeat[]][] {
  const groups = new Map<number, DisplayBeat[]>()
  for (const b of beats) {
    const bucket = roundBucket(b.roundIndex)
    const list = groups.get(bucket) ?? []
    list.push(b)
    groups.set(bucket, list)
  }
  return [...groups.entries()].sort((a, b) => a[0] - b[0])
}
