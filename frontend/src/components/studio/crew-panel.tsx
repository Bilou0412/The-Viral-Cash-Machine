// La salle de production : les agents-métiers de la phase courante, chacun sous
// forme de carte (qui fait quoi, ce qu'il produit) + une action « Diriger »
// optionnelle fournie par le parent.

import type { ReactNode } from "react"
import { crewForPhase, type CrewRole, type PhaseKey } from "@/lib/crew"

export function CrewPanel({
  phase,
  renderAction,
}: {
  phase: PhaseKey
  renderAction?: (role: CrewRole) => ReactNode
}) {
  const roles = crewForPhase(phase)
  if (roles.length === 0) return null
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {roles.map((role) => {
        const Icon = role.icon
        return (
          <div
            key={role.key}
            className="flex flex-col gap-2 rounded-xl border border-border bg-card/40 p-3"
          >
            <div className="flex items-start gap-2.5">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon className="h-4.5 w-4.5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold leading-tight">{role.title}</p>
                <p className="text-xs text-muted-foreground">{role.subtitle}</p>
              </div>
            </div>
            {renderAction?.(role)}
          </div>
        )
      })}
    </div>
  )
}
