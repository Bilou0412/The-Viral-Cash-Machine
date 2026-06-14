import { Link } from "react-router-dom"
import { ChevronLeft } from "lucide-react"
import { useEpisode } from "@/hooks/use-studio"

/**
 * Small back-link from an episode page to its owning project. Resolves the
 * project id from the episode itself, so callers only pass the episode id.
 * Renders nothing until the episode (and thus its project_id) is known.
 */
export function ProjectBreadcrumb({ episodeId }: { episodeId: number }) {
  const episode = useEpisode(episodeId)
  const projectId = episode.data?.project_id
  if (projectId == null) return null
  return (
    <Link
      to={`/projects/${projectId}`}
      className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
    >
      <ChevronLeft className="h-3.5 w-3.5" /> Projet
    </Link>
  )
}
