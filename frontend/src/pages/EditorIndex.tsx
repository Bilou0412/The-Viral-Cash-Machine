// /editor — entry point for the brick editor: pick a project, create a document
// (→ navigates to /editor/:id), or open an existing one. The editor itself is the
// full-screen /editor/:docId route.

import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Clapperboard, Plus } from "lucide-react"
import { useProjects } from "@/hooks/use-studio"
import { useCreateEditorDocument, useEditorDocuments } from "@/hooks/use-editor"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { EmptyState, ErrorState, LoadingState } from "@/components/studio/states"

export function EditorIndex() {
  const navigate = useNavigate()
  const projects = useProjects()
  // Projet sélectionné : null = « pas encore choisi » → on retombe sur le premier
  // projet chargé (dérivé au rendu, pas synchronisé via un effet).
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  const [title, setTitle] = useState("Nouveau montage")
  const projectId = selectedProjectId ?? projects.data?.[0]?.id ?? 0

  const docs = useEditorDocuments(projectId)
  const create = useCreateEditorDocument()

  async function onCreate() {
    if (!projectId) {
      toast.error("Crée d'abord un projet")
      return
    }
    try {
      const doc = await create.mutateAsync({ project_id: projectId, title })
      navigate(`/editor/${doc.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Création impossible")
    }
  }

  if (projects.isLoading) return <LoadingState label="Chargement…" />
  if (projects.isError) return <ErrorState error={projects.error} />
  if (!projects.data || projects.data.length === 0) {
    return (
      <EmptyState
        title="Aucun projet"
        description="Crée un projet pour démarrer un montage."
        action={
          <Button asChild>
            <Link to="/projects">Aller aux projets</Link>
          </Button>
        }
      />
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Éditeur</h1>
        <p className="text-sm text-muted-foreground">
          Compose ta vidéo brique par brique sur une timeline.
        </p>
      </div>

      {/* Create */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 p-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Projet</label>
            <select
              value={projectId}
              onChange={(e) => setSelectedProjectId(Number(e.target.value))}
              className="h-9 rounded-md border border-border bg-background px-3 text-sm"
            >
              {projects.data.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="editor-doc-title" className="text-xs text-muted-foreground">Titre</label>
            <Input id="editor-doc-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <Button onClick={onCreate} disabled={create.isPending}>
            <Plus className="h-4 w-4" /> Nouveau document
          </Button>
        </CardContent>
      </Card>

      {/* Existing documents */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
          Documents de ce projet
        </h2>
        {docs.isLoading ? (
          <LoadingState label="Chargement…" />
        ) : docs.data && docs.data.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {docs.data.map((d) => (
              <Card key={d.id} className="transition-colors hover:border-primary/60">
                <CardContent className="flex items-center gap-3 p-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md bg-secondary">
                    <Clapperboard className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{d.title}</p>
                    <p className="text-xs text-muted-foreground">#{d.id}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Link to={`/editor/${d.id}/review`} className="text-xs font-medium text-primary hover:underline">
                      Réviser
                    </Link>
                    <Link to={`/editor/${d.id}`} className="text-xs text-muted-foreground hover:underline">
                      Montage
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Aucun document pour l'instant — crée-en un ci-dessus.
          </p>
        )}
      </div>
    </div>
  )
}
