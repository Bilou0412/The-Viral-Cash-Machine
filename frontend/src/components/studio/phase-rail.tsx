// La colonne vertébrale du studio : les 5 phases du cinéma en stepper.
// Développement → Préproduction → Tournage → Postproduction → Distribution.

import { Check } from "lucide-react"
import { PHASES, type PhaseKey } from "@/lib/crew"
import { cn } from "@/lib/utils"

export function PhaseRail({
  current,
  onSelect,
}: {
  current: PhaseKey
  onSelect?: (phase: PhaseKey) => void
}) {
  const currentIndex = PHASES.findIndex((p) => p.key === current)
  return (
    <div className="flex w-full items-stretch gap-1 overflow-x-auto rounded-xl border border-border bg-card/40 p-1.5">
      {PHASES.map((p, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "current" : "todo"
        return (
          <button
            key={p.key}
            type="button"
            onClick={() => onSelect?.(p.key)}
            className={cn(
              "flex min-w-[9rem] flex-1 flex-col rounded-lg px-3 py-2 text-left transition-colors",
              state === "current"
                ? "bg-primary/15 ring-1 ring-primary"
                : "hover:bg-secondary/60",
            )}
          >
            <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <span
                className={cn(
                  "flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold",
                  state === "done"
                    ? "bg-primary text-primary-foreground"
                    : state === "current"
                      ? "bg-primary/30 text-foreground"
                      : "bg-secondary text-muted-foreground",
                )}
              >
                {state === "done" ? <Check className="h-2.5 w-2.5" /> : i + 1}
              </span>
              Phase {i + 1}
            </span>
            <span
              className={cn(
                "mt-1 text-sm font-semibold leading-tight",
                state === "current" ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {p.title}
            </span>
            <span className="text-[11px] leading-tight text-muted-foreground/70">
              {p.subtitle}
            </span>
          </button>
        )
      })}
    </div>
  )
}
