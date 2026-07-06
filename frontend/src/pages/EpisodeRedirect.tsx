import { Navigate, useParams } from "react-router-dom"
import { LoadingState, ErrorState } from "@/components/studio/states"
import { useEpisode } from "@/hooks/use-studio"
import { useEpisodeDocument } from "@/hooks/use-editor"

/** /episodes/:id → route vers l'écran le plus pertinent pour l'épisode.
 *
 * Priorité au **document de scènes** : une vidéo créée via « Créer » s'ouvre sur
 * sa **revue** (`/editor/:docId/review`) — prompts éditables. Sinon (épisode
 * aventure legacy, sans document), on retombe sur la destination liée au statut. */
export function EpisodeRedirect() {
  const { id } = useParams()
  const episodeId = Number(id)
  const episode = useEpisode(episodeId)
  const doc = useEpisodeDocument(episodeId)

  // On attend la résolution du document (succès OU 404) avant de router, pour ne
  // pas rediriger vers le legacy alors qu'une revue par scènes existe.
  if (episode.isLoading || doc.isLoading) return <LoadingState />
  if (episode.isError) return <ErrorState error={episode.error} />

  if (doc.data) return <Navigate to={`/editor/${doc.data.id}/review`} replace />

  const ep = episode.data!
  const dest =
    ep.status === "done"
      ? "montage"
      : ep.status === "assets" || ep.status === "montage"
        ? "assets"
        : "script"
  return <Navigate to={`/episodes/${episodeId}/${dest}`} replace />
}
