import { Navigate, useParams } from "react-router-dom"
import { LoadingState, ErrorState } from "@/components/studio/states"
import { useEpisode } from "@/hooks/use-studio"

/** /episodes/:id → routes to the most relevant screen for the episode's status. */
export function EpisodeRedirect() {
  const { id } = useParams()
  const episodeId = Number(id)
  const episode = useEpisode(episodeId)

  if (episode.isLoading) return <LoadingState />
  if (episode.isError) return <ErrorState error={episode.error} />

  const ep = episode.data!
  const dest =
    ep.status === "done"
      ? "montage"
      : ep.status === "assets" || ep.status === "montage"
        ? "assets"
        : "script"
  return <Navigate to={`/episodes/${episodeId}/${dest}`} replace />
}
