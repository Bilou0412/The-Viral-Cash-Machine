// /templates/:id — CONSTRUCTEUR de template : on bâtit la STRUCTURE (le contenant)
// sur une timeline de montage. On ajoute des briques vidéo/photo, on règle leur
// durée / format / narration, on réordonne. Aucun contenu ici — GPT le remplira
// (T2). La timeline bouge en direct ; sauvegarde automatique.

import { useCallback, useMemo, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"
import {
  ArrowLeft,
  ArrowRight,
  Film,
  Image as ImageIcon,
  Mic,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react"
import { useSaveTemplate, useTemplate } from "@/hooks/use-templates"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"
import type { TemplateSlot } from "@/lib/types"

const SAVE_DEBOUNCE_MS = 500
const PX_PER_SEC = 64
const RULER_H = 20
const LANE_H = 72
const GUTTER = 68
const MIN_BLOCK_PX = 44
const ASPECTS = ["9:16", "16:9", "1:1"]
const RESOLUTIONS = ["720p", "1080p", "2K"]

const newSlot = (kind: "video" | "photo"): TemplateSlot => ({
  id: crypto.randomUUID(),
  kind,
  duration: kind === "video" ? 4 : 3,
  aspect_ratio: "9:16",
  resolution: "720p",
  narration: true,
})

/** Positions cumulées : les slots s'enchaînent dans l'ordre de la liste. */
function withStarts(slots: TemplateSlot[]): { slot: TemplateSlot; start: number }[] {
  let acc = 0
  return slots.map((slot) => {
    const start = acc
    acc += slot.duration
    return { slot, start }
  })
}

function SlotBlock({
  left,
  width,
  tone,
  selected,
  onSelect,
  icon: Icon,
  badge,
  label,
}: {
  left: number
  width: number
  tone: "video" | "audio"
  selected: boolean
  onSelect: () => void
  icon: typeof ImageIcon
  badge?: string
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      title={label}
      className={cn(
        "absolute top-1.5 flex h-[calc(100%-0.75rem)] flex-col justify-between overflow-hidden rounded-md border px-2 py-1.5 text-left transition",
        tone === "video" ? "bg-primary/10 hover:border-primary/60" : "bg-emerald-500/10 hover:border-emerald-500/60",
        selected
          ? "border-primary ring-2 ring-primary"
          : tone === "video"
            ? "border-primary/30"
            : "border-emerald-500/30"
      )}
      style={{ left, width }}
    >
      <div className="flex items-center gap-1.5">
        {badge && (
          <span className="flex h-4 min-w-4 items-center justify-center rounded bg-background/80 px-1 text-[10px] font-bold">
            {badge}
          </span>
        )}
        <Icon className={cn("h-3.5 w-3.5 shrink-0", tone === "video" ? "text-primary" : "text-emerald-500")} />
      </div>
      <span className="line-clamp-2 text-[11px] font-medium leading-tight">{label}</span>
    </button>
  )
}

export function TemplateBuilder() {
  const { id = "" } = useParams()
  const { data: template, isLoading, isError } = useTemplate(id)
  const saveM = useSaveTemplate(id)

  const [name, setName] = useState("")
  const [slots, setSlots] = useState<TemplateSlot[]>([])
  const [hydratedKey, setHydratedKey] = useState<string | null>(null)
  const [selId, setSelId] = useState<string | null>(null)
  const serverKey = template ? JSON.stringify(template) : null
  if (serverKey && hydratedKey !== serverKey && template) {
    setHydratedKey(serverKey)
    setName(template.name)
    setSlots(template.slots)
  }

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const commit = useCallback(
    (nextName: string, nextSlots: TemplateSlot[]) => {
      setName(nextName)
      setSlots(nextSlots)
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(
        () => saveM.mutate({ name: nextName, slots: nextSlots }),
        SAVE_DEBOUNCE_MS
      )
    },
    [saveM]
  )

  const addSlot = (kind: "video" | "photo") => {
    const s = newSlot(kind)
    commit(name, [...slots, s])
    setSelId(s.id)
  }
  const patchSlot = (slotId: string, patch: Partial<TemplateSlot>) =>
    commit(name, slots.map((s) => (s.id === slotId ? { ...s, ...patch } : s)))
  const removeSlot = (slotId: string) => {
    commit(name, slots.filter((s) => s.id !== slotId))
    if (selId === slotId) setSelId(null)
  }
  const moveSlot = (slotId: string, dir: -1 | 1) => {
    const i = slots.findIndex((s) => s.id === slotId)
    const j = i + dir
    const a = slots[i]
    const b = slots[j]
    if (!a || !b) return
    const next = slots.slice()
    next[i] = b
    next[j] = a
    commit(name, next)
  }

  const placed = useMemo(() => withStarts(slots), [slots])
  const totalSec = Math.max(6, placed.reduce((a, p) => a + p.slot.duration, 0))
  const stripWidth = totalSec * PX_PER_SEC + 16
  const selected = slots.find((s) => s.id === selId) ?? null
  const selIndex = selected ? slots.findIndex((s) => s.id === selected.id) : -1

  if (isError) return <div className="p-8 text-sm text-destructive">Template introuvable.</div>
  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Chargement…</div>

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <Link to="/templates" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Templates
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0 flex-1">
          <Input
            value={name}
            onChange={(e) => commit(e.target.value, slots)}
            placeholder="Nom du template"
            className="max-w-md text-lg font-semibold"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            La structure (le contenant) : {slots.length} plan{slots.length > 1 ? "s" : ""} ·{" "}
            {totalSec.toFixed(1)}s. GPT remplira le contenu ensuite.
          </p>
        </div>
        <Button variant="outline" onClick={() => toast.info("Remplissage GPT : bientôt (T2).")}>
          <Sparkles className="h-4 w-4" /> Remplir avec l'IA
        </Button>
      </div>

      {/* Palette d'ajout */}
      <div className="flex gap-2">
        <Button variant="secondary" size="sm" onClick={() => addSlot("video")}>
          <Plus className="h-4 w-4" /> <Film className="h-4 w-4" /> Brique vidéo
        </Button>
        <Button variant="secondary" size="sm" onClick={() => addSlot("photo")}>
          <Plus className="h-4 w-4" /> <ImageIcon className="h-4 w-4" /> Brique photo
        </Button>
      </div>

      {/* Timeline multipiste */}
      <div className="rounded-xl border border-border bg-card/40 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Timeline
          </span>
          <span className="text-[11px] text-muted-foreground">{totalSec.toFixed(1)}s</span>
        </div>
        {slots.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Ajoute des briques vidéo / photo pour composer la structure.
          </p>
        ) : (
          <div className="flex">
            <div className="shrink-0" style={{ width: GUTTER }}>
              <div style={{ height: RULER_H }} />
              <div className="flex items-center gap-1 border-t border-border/40 pt-1 text-[10px] font-medium uppercase text-muted-foreground" style={{ height: LANE_H }}>
                <Film className="h-3 w-3" /> Vidéo
              </div>
              <div className="flex items-center gap-1 border-t border-border/40 pt-1 text-[10px] font-medium uppercase text-muted-foreground" style={{ height: LANE_H }}>
                <Mic className="h-3 w-3" /> Son
              </div>
            </div>
            <div className="min-w-0 flex-1 overflow-x-auto pb-2">
              <div className="relative" style={{ width: stripWidth }}>
                <div className="relative" style={{ height: RULER_H }}>
                  {Array.from({ length: Math.ceil(totalSec) + 1 }).map((_, s) => (
                    <div key={s} className="absolute top-0 h-full border-l border-border/40 text-[9px] text-muted-foreground" style={{ left: s * PX_PER_SEC }}>
                      <span className="pl-1">{s}s</span>
                    </div>
                  ))}
                </div>
                {/* piste VIDÉO */}
                <div className="relative border-t border-border/40" style={{ height: LANE_H }}>
                  {placed.map(({ slot, start }, i) => (
                    <SlotBlock
                      key={slot.id}
                      tone="video"
                      left={start * PX_PER_SEC}
                      width={Math.max(MIN_BLOCK_PX, slot.duration * PX_PER_SEC - 4)}
                      selected={selId === slot.id}
                      onSelect={() => setSelId(slot.id)}
                      icon={slot.kind === "video" ? Film : ImageIcon}
                      badge={String(i + 1)}
                      label={`${slot.kind === "video" ? "Vidéo" : "Photo"} · ${slot.duration}s · ${slot.aspect_ratio}`}
                    />
                  ))}
                </div>
                {/* piste SON */}
                <div className="relative border-t border-border/40" style={{ height: LANE_H }}>
                  {placed
                    .filter(({ slot }) => slot.narration)
                    .map(({ slot, start }) => (
                      <SlotBlock
                        key={slot.id}
                        tone="audio"
                        left={start * PX_PER_SEC}
                        width={Math.max(MIN_BLOCK_PX, slot.duration * PX_PER_SEC - 4)}
                        selected={selId === slot.id}
                        onSelect={() => setSelId(slot.id)}
                        icon={Mic}
                        label="Narration"
                      />
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Inspecteur du slot sélectionné */}
      {selected && (
        <div className="rounded-xl border border-border bg-card/40 p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-base font-semibold">Brique {selIndex + 1}</h2>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" onClick={() => moveSlot(selected.id, -1)} disabled={selIndex <= 0} title="Reculer">
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => moveSlot(selected.id, 1)} disabled={selIndex >= slots.length - 1} title="Avancer">
                <ArrowRight className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => removeSlot(selected.id)} title="Supprimer" className="text-muted-foreground hover:text-destructive">
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs">Type</Label>
              <div className="flex gap-2">
                {(["video", "photo"] as const).map((k) => (
                  <Button
                    key={k}
                    type="button"
                    variant={selected.kind === k ? "default" : "outline"}
                    size="sm"
                    onClick={() => patchSlot(selected.id, { kind: k })}
                    className="flex-1 gap-1.5"
                  >
                    {k === "video" ? <Film className="h-4 w-4" /> : <ImageIcon className="h-4 w-4" />}
                    {k === "video" ? "Vidéo" : "Photo"}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dur" className="text-xs">Durée (secondes)</Label>
              <Input
                id="dur"
                type="number"
                min={0.5}
                step={0.5}
                value={selected.duration}
                onChange={(e) => {
                  const n = parseFloat(e.target.value)
                  patchSlot(selected.id, { duration: Number.isNaN(n) ? 0.5 : Math.max(0.5, n) })
                }}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="ar" className="text-xs">Format</Label>
              <select
                id="ar"
                value={selected.aspect_ratio}
                onChange={(e) => patchSlot(selected.id, { aspect_ratio: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {ASPECTS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="res" className="text-xs">Résolution</Label>
              <select
                id="res"
                value={selected.resolution}
                onChange={(e) => patchSlot(selected.id, { resolution: e.target.value })}
                className="flex h-9 w-full rounded-md border border-input bg-background/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {RESOLUTIONS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 sm:col-span-2">
              <Switch
                id="narr"
                checked={selected.narration}
                onCheckedChange={(c) => patchSlot(selected.id, { narration: c })}
              />
              <Label htmlFor="narr" className="text-xs">
                Narration (une brique son sur ce plan)
              </Label>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
