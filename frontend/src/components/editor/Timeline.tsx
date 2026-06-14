// Bottom timeline: horizontal lanes with absolutely-positioned brick blocks on a
// px-per-second scale. Drag a block to move it; drag its right edge to change its
// duration; drop a palette chip (or click one) to add a brick. Click selects.
// Lanes are ALWAYS shown (even on an empty doc) so there is always a visible drop
// target. Deliberately a lightweight NLE — robust over feature-complete.

import { useMemo, useRef, useState } from "react"
import { Link2 } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  BRICK_COLORS,
  MIME,
  asBrickRef,
  brickRefLabel,
  type PaletteItem,
} from "./brick-helpers"
import { isGenerativeBrick, type Brick, type EditorDoc } from "@/lib/types"

const PX_PER_SEC = 64
const TRACK_H = 56
const RULER_H = 22
const MIN_DUR = 0.5

// Lanes always present, even with no tracks saved on the doc yet.
const DEFAULT_ROLES: Record<number, string> = { 0: "vidéo", 1: "overlay", 2: "audio" }
const roleFor = (i: number): string => DEFAULT_ROLES[i] ?? "vidéo"

interface TimelineProps {
  doc: EditorDoc
  selectedId: string | null
  generatedIds: Set<string>
  onSelect: (id: string) => void
  onMoveBrick: (id: string, start: number, track: number) => void
  onResizeBrick: (id: string, duration: number) => void
  onDropPalette: (item: PaletteItem, track: number, start: number) => void
}

function brickConnections(b: Brick): string[] {
  if (!isGenerativeBrick(b)) return []
  const out: string[] = []
  for (const v of Object.values(b.params)) {
    const ref = asBrickRef(v)
    if (ref) out.push(ref)
  }
  return out
}

interface DragState {
  brickId: string
  mode: "move" | "resize"
  pointerStartX: number
  origStart: number
  origDuration: number
  track: number
}

function brickLabel(b: Brick): string {
  if (b.type === "text") {
    const t = b.payload.text
    return typeof t === "string" && t ? t : "Texte"
  }
  if (b.type === "media") return "Média"
  const ref = b.model_ref || b.type
  return ref.split("/").pop() ?? b.type
}

const snap = (v: number) => Math.max(0, Math.round(v * 2) / 2)

export function Timeline({
  doc,
  selectedId,
  generatedIds,
  onSelect,
  onMoveBrick,
  onResizeBrick,
  onDropPalette,
}: TimelineProps) {
  const labelFor = (id: string) => {
    const b = doc.bricks.find((x) => x.id === id)
    return b ? brickRefLabel(b) : id
  }
  const laneRef = useRef<HTMLDivElement>(null)
  const [drag, setDrag] = useState<DragState | null>(null)

  // Lanes = default 0/1/2 ∪ doc.tracks ∪ any track referenced by a brick.
  const lanes = useMemo(() => {
    const idx = new Set<number>([0, 1, 2])
    doc.tracks.forEach((t) => idx.add(t.index))
    doc.bricks.forEach((b) => idx.add(b.placement.track))
    return [...idx]
      .sort((a, b) => a - b)
      .map((i) => ({
        index: i,
        role: doc.tracks.find((t) => t.index === i)?.role ?? roleFor(i),
      }))
  }, [doc.tracks, doc.bricks])

  const totalSec = Math.max(
    12,
    ...doc.bricks.map((b) => b.placement.start + b.placement.duration)
  )
  const widthPx = totalSec * PX_PER_SEC + 80

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag) return
    const dx = (e.clientX - drag.pointerStartX) / PX_PER_SEC
    if (drag.mode === "move") {
      onMoveBrick(drag.brickId, snap(drag.origStart + dx), drag.track)
    } else {
      onResizeBrick(drag.brickId, Math.max(MIN_DUR, snap(drag.origDuration + dx)))
    }
  }

  const endDrag = () => setDrag(null)

  const xFromEvent = (e: React.DragEvent): number => {
    const rect = laneRef.current?.getBoundingClientRect()
    const x = rect ? e.clientX - rect.left + (laneRef.current?.scrollLeft ?? 0) : 0
    return snap(x / PX_PER_SEC)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Timeline
        </span>
        <span className="text-[11px] text-muted-foreground">{totalSec.toFixed(1)}s</span>
      </div>
      <div
        ref={laneRef}
        className="relative flex-1 overflow-x-auto overflow-y-hidden"
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
      >
        <div style={{ width: widthPx }}>
          {/* ruler */}
          <div className="relative" style={{ height: RULER_H }}>
            {Array.from({ length: Math.ceil(totalSec) + 1 }).map((_, s) => (
              <div
                key={s}
                className="absolute top-0 h-full border-l border-border/50 text-[9px] text-muted-foreground"
                style={{ left: s * PX_PER_SEC }}
              >
                <span className="pl-1">{s}s</span>
              </div>
            ))}
          </div>
          {/* lanes */}
          {lanes.map((track) => (
            <div
              key={track.index}
              className="relative border-t border-border/40"
              style={{ height: TRACK_H }}
              onDragOver={(e) => {
                e.preventDefault()
                e.dataTransfer.dropEffect = "copy"
              }}
              onDrop={(e) => {
                const raw = e.dataTransfer.getData(MIME)
                if (!raw) return
                e.preventDefault()
                try {
                  const item = JSON.parse(raw) as PaletteItem
                  onDropPalette(item, track.index, xFromEvent(e))
                } catch {
                  /* ignore malformed payload */
                }
              }}
            >
              <span className="pointer-events-none absolute left-1 top-1 z-10 text-[9px] uppercase tracking-wider text-muted-foreground/60">
                {track.role}
              </span>
              {doc.bricks
                .filter((b) => b.placement.track === track.index)
                .map((b) => {
                  const c = BRICK_COLORS[b.type]
                  const selected = b.id === selectedId
                  const generated = generatedIds.has(b.id)
                  const connections = brickConnections(b)
                  const connTip =
                    connections.length > 0
                      ? `Connecté à : ${connections.map(labelFor).join(", ")}`
                      : ""
                  return (
                    <div
                      key={b.id}
                      onPointerDown={(e) => {
                        onSelect(b.id)
                        setDrag({
                          brickId: b.id,
                          mode: "move",
                          pointerStartX: e.clientX,
                          origStart: b.placement.start,
                          origDuration: b.placement.duration,
                          track: track.index,
                        })
                      }}
                      className={cn(
                        "absolute top-2 flex h-[calc(100%-1rem)] cursor-grab select-none items-center overflow-hidden rounded-md border pl-2 pr-3 text-[11px] font-medium active:cursor-grabbing",
                        c.bg,
                        c.text,
                        selected ? "border-primary ring-1 ring-primary" : c.border
                      )}
                      style={{
                        left: b.placement.start * PX_PER_SEC,
                        width: Math.max(28, b.placement.duration * PX_PER_SEC - 4),
                      }}
                      title={connTip ? `${brickLabel(b)} — ${connTip}` : brickLabel(b)}
                    >
                      <span
                        className={cn(
                          "mr-1.5 h-2 w-2 shrink-0 rounded-full",
                          generated ? c.dot : "border border-current bg-transparent opacity-50"
                        )}
                        title={generated ? "généré" : "non généré"}
                      />
                      <span className="truncate">{brickLabel(b)}</span>
                      {connections.length > 0 && (
                        <Link2 className="ml-1 h-3 w-3 shrink-0 opacity-80" aria-label={connTip} />
                      )}
                      {/* resize handle (right edge) → change duration */}
                      <span
                        onPointerDown={(e) => {
                          e.stopPropagation()
                          onSelect(b.id)
                          setDrag({
                            brickId: b.id,
                            mode: "resize",
                            pointerStartX: e.clientX,
                            origStart: b.placement.start,
                            origDuration: b.placement.duration,
                            track: track.index,
                          })
                        }}
                        className="absolute right-0 top-0 h-full w-2 cursor-ew-resize bg-foreground/20 hover:bg-foreground/40"
                        title="Glisser pour changer la durée"
                      />
                    </div>
                  )
                })}
            </div>
          ))}
        </div>

        {/* Empty-state hint */}
        {doc.bricks.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <p className="rounded-md border border-dashed border-border px-4 py-2 text-xs text-muted-foreground">
              Glisse une brique depuis la gauche sur une piste — ou clique-la pour l'ajouter.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
