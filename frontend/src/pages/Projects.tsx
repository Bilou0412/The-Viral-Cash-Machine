import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { FolderKanban, FolderPlus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { EmptyState, ErrorState, LoadingState, Spinner } from "@/components/studio/states"
import { useCreateProject, useProjects } from "@/hooks/use-studio"
import { formatDate } from "@/lib/utils"

export function Projects() {
  const navigate = useNavigate()
  const projects = useProjects()
  const createProject = useCreateProject()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")

  async function submitProject() {
    if (!name.trim()) return
    try {
      const p = await createProject.mutateAsync(name.trim())
      toast.success("Projet créé")
      setName("")
      setOpen(false)
      navigate(`/projects/${p.id}`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la création")
    }
  }

  const list = projects.data ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Projets</h1>
          <p className="text-sm text-muted-foreground">
            Tes projets Aventure. Ouvre un projet pour voir ses épisodes.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>
              <FolderPlus className="h-4 w-4" /> Créer un projet
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nouveau projet</DialogTitle>
            </DialogHeader>
            <div className="space-y-2">
              <Label htmlFor="pname">Nom du projet</Label>
              <Input
                id="pname"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Horror Shorts FR"
                onKeyDown={(e) => e.key === "Enter" && submitProject()}
              />
            </div>
            <DialogFooter>
              <Button onClick={submitProject} disabled={createProject.isPending || !name.trim()}>
                {createProject.isPending && <Spinner />} Créer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {projects.isLoading ? (
        <LoadingState />
      ) : projects.isError ? (
        <ErrorState error={projects.error} />
      ) : list.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="h-8 w-8" />}
          title="Aucun projet"
          description="Crée ton premier projet pour organiser tes épisodes."
          action={
            <Button onClick={() => setOpen(true)}>
              <FolderPlus className="h-4 w-4" /> Créer un projet
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...list]
            .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
            .map((p) => (
              <button
                key={p.id}
                onClick={() => navigate(`/projects/${p.id}`)}
                className="text-left"
              >
                <Card className="h-full transition-colors hover:border-primary/40 hover:bg-secondary/40">
                  <CardHeader className="flex-row items-center gap-3 space-y-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-muted-foreground">
                      <FolderKanban className="h-5 w-5" />
                    </div>
                    <CardTitle className="truncate text-base">{p.name}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xs text-muted-foreground">
                      Créé le {formatDate(p.created_at)}
                    </p>
                  </CardContent>
                </Card>
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
