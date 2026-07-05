// /prompt-templates — bibliothèque de templates de prompt système (l'identité).
// L'éditeur (identité + rôles à trous) vit dans /prompt-templates/:id.

import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Sparkles, Plus, Trash2, ListChecks, SquareStack } from "lucide-react"
import {
  useCreatePromptTemplate,
  useDeletePromptTemplate,
  usePromptTemplates,
} from "@/hooks/use-prompt-templates"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState, ErrorState, LoadingState } from "@/components/studio/states"

export function PromptTemplatesIndex() {
  const navigate = useNavigate()
  const list = usePromptTemplates()
  const create = useCreatePromptTemplate()
  const remove = useDeletePromptTemplate()
  const [busy, setBusy] = useState(false)

  async function onCreate() {
    setBusy(true)
    try {
      const t = await create.mutateAsync({ name: "Nouveau style", identity: "", roles: [] })
      void navigate(`/prompt-templates/${t.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Création impossible")
    } finally {
      setBusy(false)
    }
  }

  async function onDelete(id: string, name: string) {
    if (!confirm(`Supprimer le style « ${name} » ?`)) return
    try {
      await remove.mutateAsync(id)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Suppression impossible")
    }
  }

  if (list.isLoading) return <LoadingState label="Chargement…" />
  if (list.isError) return <ErrorState error={list.error} />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight">
            <Sparkles className="h-5 w-5" /> Styles (prompts système)
          </h1>
          <p className="text-sm text-muted-foreground">
            L'identité de tes vidéos : la trame scénaristique à trous. Un prompt par
            brique/rôle ; les trous deviennent le questionnaire à remplir.
          </p>
        </div>
        <Button onClick={onCreate} disabled={busy}>
          <Plus className="h-4 w-4" /> Nouveau style
        </Button>
      </div>

      {!list.data || list.data.length === 0 ? (
        <EmptyState
          title="Aucun style"
          description="Crée un style pour définir l'identité et la trame narrative réutilisable."
          action={
            <Button onClick={onCreate} disabled={busy}>
              <Plus className="h-4 w-4" /> Nouveau style
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {list.data.map((t) => (
            <Card key={t.id} className="transition-colors hover:border-primary/60">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary">
                  <Sparkles className="h-4 w-4" />
                </div>
                <Link to={`/prompt-templates/${t.id}`} className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{t.name}</p>
                  <p className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <SquareStack className="h-3 w-3" /> {t.role_count} rôle{t.role_count > 1 ? "s" : ""}
                    </span>
                    <span className="flex items-center gap-1">
                      <ListChecks className="h-3 w-3" /> {t.hole_count} trou{t.hole_count > 1 ? "s" : ""}
                    </span>
                  </p>
                </Link>
                <button
                  type="button"
                  onClick={() => onDelete(t.id, t.name)}
                  title="Supprimer"
                  className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
