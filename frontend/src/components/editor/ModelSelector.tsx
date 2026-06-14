// Model picker for a generative brick: the 3 preferred models from the brick
// contract as quick chips, plus a "search more" box backed by searchModels.

import { useState } from "react"
import { Search } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useModelSearch } from "@/hooks/use-editor"
import { cn } from "@/lib/utils"
import type { GenerativeKind } from "@/lib/types"

interface ModelSelectorProps {
  kind: GenerativeKind
  preferred: string[]
  value: string
  onChange: (modelRef: string) => void
}

export function ModelSelector({ kind, preferred, value, onChange }: ModelSelectorProps) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const { data: results, isFetching } = useModelSearch(kind, query, open && query.trim().length > 1)

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-muted-foreground">Modèle</span>
      <div className="flex flex-wrap gap-1.5">
        {preferred.map((ref) => (
          <button
            key={ref}
            type="button"
            onClick={() => onChange(ref)}
            className={cn(
              "rounded-md border px-2 py-1 text-[11px] transition-colors",
              value === ref
                ? "border-primary bg-primary/15 text-foreground"
                : "border-border bg-secondary/40 text-muted-foreground hover:bg-secondary"
            )}
          >
            {ref.split("/").pop()}
          </button>
        ))}
      </div>

      {value && !preferred.includes(value) && (
        <div className="rounded-md border border-primary bg-primary/10 px-2 py-1 text-[11px]">
          {value}
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[11px] text-accent hover:underline"
      >
        <Search className="h-3 w-3" />
        {open ? "Masquer la recherche" : "Chercher d'autres modèles"}
      </button>

      {open && (
        <div className="flex flex-col gap-1.5">
          <Input
            type="text"
            placeholder={`Rechercher un modèle ${kind}…`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-8 text-xs"
          />
          {isFetching && <span className="text-[10px] text-muted-foreground">Recherche…</span>}
          <div className="flex max-h-40 flex-col gap-1 overflow-y-auto">
            {results?.map((m) => {
              const ref = `${m.owner}/${m.name}`
              return (
                <button
                  key={ref}
                  type="button"
                  onClick={() => { onChange(ref); setOpen(false) }}
                  className="flex flex-col rounded-md border border-border bg-secondary/30 px-2 py-1.5 text-left hover:bg-secondary"
                >
                  <span className="text-[11px] font-medium">{ref}</span>
                  <span className="truncate text-[10px] text-muted-foreground">{m.description}</span>
                </button>
              )
            })}
            {results && results.length === 0 && query.trim().length > 1 && !isFetching && (
              <span className="text-[10px] text-muted-foreground">Aucun résultat.</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
