import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { Plus, FolderPlus, Clapperboard, Library as LibraryIcon, Clock } from "lucide-react"
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
import { EpisodeStatusBadge } from "@/components/studio/status-badge"
import { EmptyState, ErrorState, LoadingState, Spinner } from "@/components/studio/states"
import { useCreateProject, useEpisodes, useProjects } from "@/hooks/use-studio"
import { formatDate, formatDuration } from "@/lib/utils"

export function Dashboard() {
  const navigate = useNavigate()
  const projects = useProjects()
  const episodes = useEpisodes()
  const createProject = useCreateProject()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")

  const eps = episodes.data ?? []
  const doneCount = eps.filter((e) => e.status === "done").length

  async function submitProject() {
    if (!name.trim()) return
    try {
      await createProject.mutateAsync(name.trim())
      toast.success("Projet créé")
      setName("")
      setOpen(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la création")
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Vue d'ensemble de tes projets et de tes vidéos.
          </p>
        </div>
        <div className="flex gap-2">
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <FolderPlus className="h-4 w-4" /> Nouveau projet
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
          <Button asChild>
            <Link to="/creer">
              <Plus className="h-4 w-4" /> Créer une vidéo
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={<Clapperboard />} label="Épisodes" value={eps.length} />
        <StatCard icon={<FolderPlus />} label="Projets" value={(projects.data ?? []).length} />
        <StatCard icon={<LibraryIcon />} label="Vidéos finales" value={doneCount} />
      </div>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Épisodes récents
        </h2>
        {episodes.isLoading ? (
          <LoadingState />
        ) : episodes.isError ? (
          <ErrorState error={episodes.error} />
        ) : eps.length === 0 ? (
          <EmptyState
            icon={<Clapperboard className="h-8 w-8" />}
            title="Aucune vidéo"
            description="Crée ta première vidéo."
            action={
              <Button asChild>
                <Link to="/creer">
                  <Plus className="h-4 w-4" /> Créer une vidéo
                </Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-3">
            {[...eps]
              .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
              .map((ep) => (
                <button
                  key={ep.id}
                  onClick={() => navigate(`/episodes/${ep.id}`)}
                  className="group flex items-center gap-4 rounded-lg border border-border bg-card px-4 py-3 text-left transition-colors hover:border-primary/40 hover:bg-secondary/40"
                >
                  <div className="flex h-12 w-7 shrink-0 items-center justify-center rounded bg-black/60 text-[9px] uppercase tracking-widest text-muted-foreground/60">
                    9:16
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{ep.title}</p>
                    <p className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {formatDuration(ep.duration_s)}
                      </span>
                      <span>{formatDate(ep.created_at)}</span>
                    </p>
                  </div>
                  <EpisodeStatusBadge status={ep.status} />
                </button>
              ))}
          </div>
        )}
      </section>
    </div>
  )
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
          {label}
        </CardTitle>
        <span className="text-muted-foreground/60 [&_svg]:h-4 [&_svg]:w-4">{icon}</span>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}
