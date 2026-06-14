import { Link, useNavigate, useParams } from "react-router-dom"
import { ChevronLeft, Clapperboard, Clock, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { EpisodeStatusBadge } from "@/components/studio/status-badge"
import { EmptyState, ErrorState, LoadingState } from "@/components/studio/states"
import { useEpisodes, useProjects } from "@/hooks/use-studio"
import { formatDate, formatDuration } from "@/lib/utils"

export function ProjectDetail() {
  const { id } = useParams()
  const projectId = Number(id)
  const navigate = useNavigate()
  const projects = useProjects()
  const episodes = useEpisodes(projectId)

  const project = projects.data?.find((p) => p.id === projectId)
  const eps = episodes.data ?? []

  return (
    <div className="space-y-6">
      <Link
        to="/projects"
        className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronLeft className="h-3.5 w-3.5" /> Projets
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {project ? project.name : `Projet #${projectId}`}
          </h1>
          <p className="text-sm text-muted-foreground">
            {eps.length} épisode{eps.length > 1 ? "s" : ""} dans ce projet.
          </p>
        </div>
        <Button asChild>
          <Link to={`/new?project=${projectId}`}>
            <Plus className="h-4 w-4" /> Nouvel épisode
          </Link>
        </Button>
      </div>

      {episodes.isLoading ? (
        <LoadingState />
      ) : episodes.isError ? (
        <ErrorState error={episodes.error} />
      ) : eps.length === 0 ? (
        <EmptyState
          icon={<Clapperboard className="h-8 w-8" />}
          title="Aucun épisode"
          description="Lance ton premier épisode dans ce projet."
          action={
            <Button asChild>
              <Link to={`/new?project=${projectId}`}>
                <Plus className="h-4 w-4" /> Nouvel épisode
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
    </div>
  )
}
