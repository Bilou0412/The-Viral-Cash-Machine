// Bottom timeline: horizontal tracks with absolutely-positioned brick blocks on
// a px-per-second scale. Drag a block to move it (snaps start, clamps to >=0).
// Drop a palette chip onto a track to add a brick. Click selects. Deliberately a
// lightweight NLE — robust over feature-complete.

import { useRef, useState } from "react"
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

interface TimelineProps {
  doc: EditorDoc
  selectedId: string | null
  /** Ids of bricks with a ready generated asset. */
  generatedIds: Set<string>
  onSelect: (id: string) => void
  onMoveBrick: (id: string, start: number, track: number) => void
  onDropPalette: (item: PaletteItem, track: number, start: number) => void
}

// Ids of bricks this brick is connected to via "{brick:<id>}" params.
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
  pointerStartX: number
  origStart: number
  track: number
}

function brickLabel(b: Brick): string {
  if (b.type === "text") {
    const t = b.payload.text
    return typeof t === "string" && t ? t : "Texte"
  }
  if (b.type === "media") return "Média"
  // generative
  const ref = b.model_ref || b.type
  return ref.split("/").pop() ?? b.type
}

export function Timeline({
  doc,
  selectedId,
  generatedIds,
  onSelect,
  onMoveBrick,
  onDropPalette,
}: TimelineProps) {
  const labelFor = (id: string) => {
    const b = doc.bricks.find((x) => x.id === id)
    return b ? brickRefLabel(b) : id
  }
  const laneRef = useRef<HTMLDivElement>(null)
  const [drag, setDrag] = useState<DragState | null>(null)

  const totalSec = Math.max(
    12,
    ...doc.bricks.map((b) => b.placement.start + b.placement.duration)
  )
  const widthPx = totalSec * PX_PER_SEC + 80

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag) return
    const dx = e.clientX - drag.pointerStartX
    const next = Math.max(0, Math.round((drag.origStart + dx / PX_PER_SEC) * 2) / 2)
    onMoveBrick(drag.brickId, next, drag.track)
  }

  const endDrag = () => setDrag(null)

  const xFromEvent = (e: React.DragEvent): number => {
    const rect = laneRef.current?.getBoundingClientRect()
    const x = rect ? e.clientX - rect.left + (laneRef.current?.scrollLeft ?? 0) : 0
    return Math.max(0, Math.round((x / PX_PER_SEC) * 2) / 2)
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
          {/* tracks */}
          {doc.tracks.map((track) => (
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
                          pointerStartX: e.clientX,
                          origStart: b.placement.start,
                          track: track.index,
                        })
                      }}
                      className={cn(
                        "absolute top-2 flex h-[calc(100%-1rem)] cursor-grab select-none items-center overflow-hidden rounded-md border px-2 text-[11px] font-medium active:cursor-grabbing",
                        c.bg,
                        c.text,
                        selected ? "border-primary ring-1 ring-primary" : c.border
                      )}
                      style={{
                        left: b.placement.start * PX_PER_SEC,
                        width: Math.max(24, b.placement.duration * PX_PER_SEC - 4),
                      }}
                      title={
                        connTip ? `${brickLabel(b)} — ${connTip}` : brickLabel(b)
                      }
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
                        <Link2
                          className="ml-1 h-3 w-3 shrink-0 opacity-80"
                          aria-label={connTip}
                        />
                      )}
                    </div>
                  )
                })}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
