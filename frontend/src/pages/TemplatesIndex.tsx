// /templates — bibliothèque de templates réutilisables (le « contenant »).
// On crée/ouvre un template ; le constructeur (timeline) vit dans /templates/:id.

import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { LayoutTemplate, Plus, Trash2, Clock, Film } from "lucide-react"
import { useCreateTemplate, useDeleteTemplate, useTemplates } from "@/hooks/use-templates"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState, ErrorState, LoadingState } from "@/components/studio/states"

export function TemplatesIndex() {
  const navigate = useNavigate()
  const templates = useTemplates()
  const create = useCreateTemplate()
  const remove = useDeleteTemplate()
  const [busy, setBusy] = useState(false)

  async function onCreate() {
    setBusy(true)
    try {
      const t = await create.mutateAsync({ name: "Nouveau template", slots: [] })
      void navigate(`/templates/${t.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Création impossible")
    } finally {
      setBusy(false)
    }
  }

  async function onDelete(id: string, name: string) {
    if (!confirm(`Supprimer le template « ${name} » ?`)) return
    try {
      await remove.mutateAsync(id)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Suppression impossible")
    }
  }

  if (templates.isLoading) return <LoadingState label="Chargement…" />
  if (templates.isError) return <ErrorState error={templates.error} />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold tracking-tight">
            <LayoutTemplate className="h-5 w-5" /> Templates
          </h1>
          <p className="text-sm text-muted-foreground">
            Le contenant de tes vidéos : construis la structure (plans, durées, format),
            l'IA remplira le contenu ensuite.
          </p>
        </div>
        <Button onClick={onCreate} disabled={busy}>
          <Plus className="h-4 w-4" /> Nouveau template
        </Button>
      </div>

      {!templates.data || templates.data.length === 0 ? (
        <EmptyState
          title="Aucun template"
          description="Crée un template pour définir la structure d'une vidéo réutilisable."
          action={
            <Button onClick={onCreate} disabled={busy}>
              <Plus className="h-4 w-4" /> Nouveau template
            </Button>
          }
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {templates.data.map((t) => (
            <Card key={t.id} className="transition-colors hover:border-primary/60">
              <CardContent className="flex items-center gap-3 p-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary">
                  <LayoutTemplate className="h-4 w-4" />
                </div>
                <Link to={`/templates/${t.id}`} className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{t.name}</p>
                  <p className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Film className="h-3 w-3" /> {t.slot_count} plan{t.slot_count > 1 ? "s" : ""}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {t.total_duration.toFixed(1)}s
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
