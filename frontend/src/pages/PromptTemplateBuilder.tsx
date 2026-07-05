// /prompt-templates/:id — ÉDITEUR d'un template de prompt système (l'identité).
// On écrit l'identité globale + un prompt système à trous par brique/rôle. Les
// {trous} sont détectés en direct → ils formeront le questionnaire (T2.2). GPT
// remplira les trous et écrira le contenu de chaque brique (T2.3).

import { useCallback, useMemo, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  ListChecks,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react"
import { useSavePromptTemplate, usePromptTemplate } from "@/hooks/use-prompt-templates"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import type { RolePrompt } from "@/lib/types"

const SAVE_DEBOUNCE_MS = 500

/** Trous {token} uniques (ordre d'apparition) — miroir de la dérivation serveur. */
function holesOf(identity: string, roles: RolePrompt[]): string[] {
  const seen: string[] = []
  const scan = (t: string) => {
    for (const m of t.matchAll(/\{([a-zA-Z0-9_]+)\}/g)) {
      const tok = m[1]
      if (tok && !seen.includes(tok)) seen.push(tok)
    }
  }
  scan(identity)
  for (const r of roles) scan(r.prompt)
  return seen
}

const newRole = (): RolePrompt => ({ id: crypto.randomUUID(), label: "", prompt: "" })

export function PromptTemplateBuilder() {
  const { id = "" } = useParams()
  const { data: tpl, isLoading, isError } = usePromptTemplate(id)
  const saveM = useSavePromptTemplate(id)

  const [name, setName] = useState("")
  const [identity, setIdentity] = useState("")
  const [roles, setRoles] = useState<RolePrompt[]>([])
  const [hydratedKey, setHydratedKey] = useState<string | null>(null)
  const serverKey = tpl ? JSON.stringify(tpl) : null
  if (serverKey && hydratedKey !== serverKey && tpl) {
    setHydratedKey(serverKey)
    setName(tpl.name)
    setIdentity(tpl.identity)
    setRoles(tpl.roles)
  }

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const commit = useCallback(
    (nextName: string, nextIdentity: string, nextRoles: RolePrompt[]) => {
      setName(nextName)
      setIdentity(nextIdentity)
      setRoles(nextRoles)
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(
        () => saveM.mutate({ name: nextName, identity: nextIdentity, roles: nextRoles }),
        SAVE_DEBOUNCE_MS
      )
    },
    [saveM]
  )

  const addRole = () => commit(name, identity, [...roles, newRole()])
  const patchRole = (rid: string, patch: Partial<RolePrompt>) =>
    commit(name, identity, roles.map((r) => (r.id === rid ? { ...r, ...patch } : r)))
  const removeRole = (rid: string) => commit(name, identity, roles.filter((r) => r.id !== rid))
  const moveRole = (rid: string, dir: -1 | 1) => {
    const i = roles.findIndex((r) => r.id === rid)
    const j = i + dir
    const a = roles[i]
    const b = roles[j]
    if (!a || !b) return
    const next = roles.slice()
    next[i] = b
    next[j] = a
    commit(name, identity, next)
  }

  const holes = useMemo(() => holesOf(identity, roles), [identity, roles])

  if (isError) return <div className="p-8 text-sm text-destructive">Style introuvable.</div>
  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Chargement…</div>

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <Link to="/prompt-templates" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Styles
      </Link>

      <div>
        <Input
          value={name}
          onChange={(e) => commit(e.target.value, identity, roles)}
          placeholder="Nom du style"
          className="max-w-md text-lg font-semibold"
        />
        <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="h-3.5 w-3.5" /> L'identité + la trame à trous. Écris un trou avec
          des accolades, ex. <code className="rounded bg-secondary px-1">{"{lieu}"}</code>.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr,280px]">
        <div className="space-y-4">
          {/* Identité globale */}
          <div className="rounded-xl border border-border bg-card/40 p-4">
            <Label className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Identité (prompt système global)
            </Label>
            <Textarea
              rows={3}
              value={identity}
              onChange={(e) => commit(name, e.target.value, roles)}
              placeholder="Style : court-métrage d'horreur POV, {ton}, caméra à l'épaule…"
              className="mt-2"
            />
          </div>

          {/* Rôles par brique */}
          <div className="rounded-xl border border-border bg-card/40 p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Rôles (un prompt système par brique)
              </span>
              <Button variant="secondary" size="sm" onClick={addRole}>
                <Plus className="h-4 w-4" /> Ajouter un rôle
              </Button>
            </div>

            {roles.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Ajoute un rôle par brique (accroche, tension, chute…).
              </p>
            ) : (
              <div className="space-y-3">
                {roles.map((r, i) => (
                  <div key={r.id} className="rounded-lg border border-border/60 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-secondary text-[10px] font-bold">
                        {i + 1}
                      </span>
                      <Input
                        value={r.label}
                        onChange={(e) => patchRole(r.id, { label: e.target.value })}
                        placeholder="Rôle (ex. Accroche)"
                        className="h-8 max-w-xs text-sm"
                      />
                      <div className="ml-auto flex items-center gap-1">
                        <Button variant="ghost" size="icon" onClick={() => moveRole(r.id, -1)} disabled={i === 0} title="Monter">
                          <ArrowLeft className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => moveRole(r.id, 1)} disabled={i === roles.length - 1} title="Descendre">
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => removeRole(r.id)} title="Supprimer" className="text-muted-foreground hover:text-destructive">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <Textarea
                      rows={2}
                      value={r.prompt}
                      onChange={(e) => patchRole(r.id, { prompt: e.target.value })}
                      placeholder="Prompt système à trous, ex. On découvre {lieu}, une menace : {danger}."
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Trous détectés → futur questionnaire */}
        <div className="h-fit rounded-xl border border-border bg-card/40 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ListChecks className="h-4 w-4 text-primary" /> Trous détectés
          </p>
          <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
            Ces variables deviendront le questionnaire rempli par le créateur (T2).
          </p>
          {holes.length === 0 ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Aucun trou. Ajoute une variable avec <code className="rounded bg-secondary px-1">{"{…}"}</code>.
            </p>
          ) : (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {holes.map((h) => (
                <span key={h} className="rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  {h}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
