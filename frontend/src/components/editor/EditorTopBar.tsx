// Top bar: editable doc title, a collapsible global-context panel
// (text / art_direction / characters), and the Générer + Rendre actions wired to
// SSE progress. Save state is surfaced as a small indicator.

import { useState } from "react"
import { ChevronDown, Loader2, Play, Settings2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import type { EditorDoc, GlobalContext } from "@/lib/types"

interface EditorTopBarProps {
  doc: EditorDoc
  onPatchDoc: (patch: Partial<EditorDoc>) => void
  onGenerate: () => void
  onRender: () => void
  generating: boolean
  rendering: boolean
  saving: boolean
  progressLabel: string | null
}

export function EditorTopBar({
  doc,
  onPatchDoc,
  onGenerate,
  onRender,
  generating,
  rendering,
  saving,
  progressLabel,
}: EditorTopBarProps) {
  const [ctxOpen, setCtxOpen] = useState(false)

  const setCtx = (patch: Partial<GlobalContext>) =>
    onPatchDoc({ global_context: { ...doc.global_context, ...patch } })

  const charsText = Object.entries(doc.global_context.characters)
    .map(([k, v]) => `${k}: ${v}`)
    .join("\n")

  const parseChars = (raw: string): Record<string, string> => {
    const out: Record<string, string> = {}
    for (const line of raw.split("\n")) {
      const idx = line.indexOf(":")
      if (idx === -1) continue
      const k = line.slice(0, idx).trim()
      const v = line.slice(idx + 1).trim()
      if (k) out[k] = v
    }
    return out
  }

  return (
    <div className="border-b border-border bg-card/40">
      <div className="flex items-center gap-3 px-4 py-2.5">
        <Input
          value={doc.title}
          onChange={(e) => onPatchDoc({ title: e.target.value })}
          className="h-8 max-w-xs border-transparent bg-transparent text-base font-semibold focus-visible:border-input focus-visible:bg-background/60"
        />
        <span className="text-[11px] text-muted-foreground">
          {saving ? "Enregistrement…" : "Enregistré"}
        </span>

        <div className="ml-auto flex items-center gap-2">
          {progressLabel && (
            <span className="flex items-center gap-1.5 text-[11px] text-accent">
              <Loader2 className="h-3 w-3 animate-spin" />
              {progressLabel}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={() => setCtxOpen((o) => !o)}>
            <Settings2 className="h-4 w-4" />
            Contexte global
            <ChevronDown className={cn("h-3 w-3 transition-transform", ctxOpen && "rotate-180")} />
          </Button>
          <Button variant="accent" size="sm" onClick={onGenerate} disabled={generating}>
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Générer
          </Button>
          <Button size="sm" onClick={onRender} disabled={rendering}>
            {rendering ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Rendre
          </Button>
        </div>
      </div>

      {ctxOpen && (
        <div className="grid grid-cols-1 gap-3 border-t border-border px-4 py-3 md:grid-cols-3">
          <div className="flex flex-col gap-1">
            <Label className="text-[10px]">Contexte (texte)</Label>
            <Textarea rows={3} value={doc.global_context.text}
              onChange={(e) => setCtx({ text: e.target.value })} />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-[10px]">Direction artistique</Label>
            <Textarea rows={3} value={doc.global_context.art_direction}
              onChange={(e) => setCtx({ art_direction: e.target.value })} />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-[10px]">Personnages (nom: description)</Label>
            <Textarea rows={3} value={charsText}
              placeholder={"Conteur: voix grave\nÉtienne: jeune homme pâle"}
              onChange={(e) => setCtx({ characters: parseChars(e.target.value) })} />
          </div>
        </div>
      )}
    </div>
  )
}
