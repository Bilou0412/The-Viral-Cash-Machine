import { Link } from "react-router-dom"
import { Library as LibraryIcon, Play, Clock } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { EpisodeStatusBadge } from "@/components/studio/status-badge"
import { EmptyState, ErrorState, LoadingState } from "@/components/studio/states"
import { useLibrary } from "@/hooks/use-studio"
import { episodeVideoUrl } from "@/lib/api"
import { formatDuration } from "@/lib/utils"

export function LibraryPage() {
  const library = useLibrary()

  if (library.isLoading) return <LoadingState />
  if (library.isError) return <ErrorState error={library.error} />

  const videos = library.data ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bibliothèque</h1>
        <p className="text-sm text-muted-foreground">Toutes les vidéos finales prêtes à publier.</p>
      </div>

      {videos.length === 0 ? (
        <EmptyState
          icon={<LibraryIcon className="h-8 w-8" />}
          title="Aucune vidéo finale"
          description="Les épisodes montés apparaîtront ici."
          action={
            <Button asChild>
              <Link to="/new">Nouvel épisode</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {videos.map((ep) => (
            <Card key={ep.episode_id} className="group overflow-hidden">
              <Link to={`/episodes/${ep.episode_id}/montage`} className="block">
                <div className="relative aspect-vertical w-full bg-black">
                  <video
                    src={episodeVideoUrl(ep.episode_id)}
                    muted
                    playsInline
                    preload="metadata"
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 transition-opacity group-hover:opacity-100">
                    <Play className="h-8 w-8 text-white" />
                  </div>
                </div>
              </Link>
              <CardContent className="space-y-1 p-3">
                <p className="truncate text-sm font-medium">{ep.title}</p>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {formatDuration(ep.duration_s)}
                  </span>
                  <EpisodeStatusBadge status={ep.status} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
