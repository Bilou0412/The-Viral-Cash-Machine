// Left rail: the brick palette. Generative bricks come from useBricks(); the
// media/text bricks are hardcoded. Click or drag a chip to add it to the timeline.

import { Image as ImageIcon, Film, Mic, Upload, Type } from "lucide-react"
import { useBricks } from "@/hooks/use-editor"
import { cn } from "@/lib/utils"
import {
  BRICK_COLORS,
  BRICK_LABELS,
  MIME,
  STATIC_PALETTE,
  type PaletteItem,
} from "./brick-helpers"
import type { BrickType } from "@/lib/types"

const ICONS: Record<BrickType, React.ComponentType<{ className?: string }>> = {
  image: ImageIcon,
  video: Film,
  voice: Mic,
  media: Upload,
  text: Type,
}

interface BrickPaletteProps {
  onAdd: (item: PaletteItem) => void
}

export function BrickPalette({ onAdd }: BrickPaletteProps) {
  const { data: specs, isLoading } = useBricks()

  const generative: PaletteItem[] =
    specs?.map((s) => ({
      type: s.kind,
      label: BRICK_LABELS[s.kind],
      hint: s.preferred_models[0] ?? "modèle génératif",
      spec: s,
    })) ?? []

  const items = [...generative, ...STATIC_PALETTE]

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-card/40">
      <div className="px-4 pt-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Briques
      </div>
      <p className="px-4 pb-2 text-[10px] leading-snug text-muted-foreground/70">
        Glisse une brique sur la timeline, ou clique pour l'ajouter. Clique un bloc
        pour ses réglages.
      </p>
      <div className="flex flex-col gap-2 overflow-y-auto px-3 pb-4">
        {isLoading && <div className="px-1 text-xs text-muted-foreground">Chargement…</div>}
        {items.map((item) => {
          const Icon = ICONS[item.type]
          const c = BRICK_COLORS[item.type]
          return (
            <button
              key={`${item.type}-${item.label}`}
              type="button"
              draggable
              onClick={() => onAdd(item)}
              onDragStart={(e) => {
                e.dataTransfer.setData(MIME, JSON.stringify(item))
                e.dataTransfer.effectAllowed = "copy"
              }}
              className={cn(
                "group flex items-start gap-3 rounded-md border p-2.5 text-left transition-colors hover:bg-secondary/60",
                c.border,
                c.bg
              )}
            >
              <span className={cn("mt-0.5 rounded p-1.5", c.bg)}>
                <Icon className={cn("h-4 w-4", c.text)} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium">{item.label}</span>
                <span className="block truncate text-[11px] text-muted-foreground">
                  {item.hint}
                </span>
              </span>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
