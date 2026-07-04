import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { Clapperboard, Download, Film, Play, Wand2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EpisodeStatusBadge } from "@/components/studio/status-badge"
import { ErrorState, LoadingState, Spinner } from "@/components/studio/states"
import { ProjectBreadcrumb } from "@/components/studio/project-breadcrumb"
import { useCost, useEpisode, useMontage } from "@/hooks/use-studio"
import { useJobEvents } from "@/hooks/use-job-events"
import { api, episodeVideoUrl } from "@/lib/api"
import { formatCost, formatDuration } from "@/lib/utils"

export function Montage() {
  const { id } = useParams()
  const episodeId = Number(id)
  const episode = useEpisode(episodeId)
  const cost = useCost(episodeId)
  const montage = useMontage(episodeId)
  const [launched, setLaunched] = useState(false)

  // Une production est « en cours » tant qu'on l'a lancée ET que l'épisode n'a
  // pas encore de vidéo finale. Dérivé au rendu (pas de setState dans un effet) :
  // à produce_done, l'épisode passe « done » avec un final_path → le spinner
  // s'arrête et l'abonnement SSE se coupe de lui-même.
  const isProduced = episode.data?.status === "done" && !!episode.data.final_path
  const producing = launched && !isProduced

  // Subscribe to the job stream while a full production is running so the page
  // auto-refreshes on produce_done (the hook invalidates episode + library).
  useJobEvents(episodeId, producing)

  async function produceAll() {
    setLaunched(true)
    try {
      await api.produce(episodeId)
      toast.success("Production lancée 🎬", {
        description: "Vidéo complète (assets + intro + montage) en cours. " +
          "Cette page se met à jour automatiquement quand c'est prêt (~15-20 min).",
      })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec du lancement")
      setLaunched(false)
    }
    // On garde `launched` : l'abonnement SSE reste actif jusqu'à produce_done,
    // moment où l'épisode devient « done » et où `producing` se dérive à false.
  }

  if (episode.isLoading) return <LoadingState />
  if (episode.isError) return <ErrorState error={episode.error} />
  const ep = episode.data!
  const hasVideo = ep.status === "done" && !!ep.final_path

  async function assemble() {
    try {
      await montage.mutateAsync()
      toast.success("Montage terminé")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec du montage")
    }
  }

  return (
    <div className="space-y-6">
      <ProjectBreadcrumb episodeId={episodeId} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Montage & Preview</h1>
          <p className="text-sm text-muted-foreground">
            Assemble intro + 3 rounds + épilogue en une vidéo 9:16.
          </p>
        </div>
        <Button asChild variant="ghost">
          <Link to={`/episodes/${episodeId}/assets`}>Assets</Link>
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-[320px_1fr]">
        <Card>
          <CardContent className="p-3">
            <div className="aspect-vertical w-full overflow-hidden rounded-md border border-border bg-black">
              {hasVideo ? (
                <video
                  src={episodeVideoUrl(episodeId)}
                  controls
                  playsInline
                  className="h-full w-full object-contain"
                />
              ) : producing ? (
                <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
                  <Spinner className="h-7 w-7 text-primary" />
                  <span className="text-xs uppercase tracking-widest">Production en cours…</span>
                </div>
              ) : (
                <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground/50">
                  <Film className="h-8 w-8" />
                  <span className="text-xs uppercase tracking-widest">Pas encore monté</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{ep.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <Row label="Statut"><EpisodeStatusBadge status={ep.status} /></Row>
              <Row label="Durée">{formatDuration(ep.duration_s)}</Row>
              <Row label="Coût">{formatCost(cost.data?.actual_usd)}</Row>
              <Row label="Mode">{ep.draft_mode ? "Draft" : "Final"}</Row>
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button onClick={produceAll} disabled={producing}>
              {producing ? <Spinner /> : <Wand2 className="h-4 w-4" />}
              Produire toute la vidéo
            </Button>
            <Button variant="outline" onClick={assemble} disabled={montage.isPending || producing}>
              {montage.isPending ? <Spinner /> : <Clapperboard className="h-4 w-4" />}
              {hasVideo ? "Réassembler (montage seul)" : "Monter (assets déjà générés)"}
            </Button>
            {hasVideo && (
              <>
                <Button asChild variant="outline">
                  <a href={episodeVideoUrl(episodeId)} target="_blank" rel="noreferrer">
                    <Play className="h-4 w-4" /> Ouvrir
                  </a>
                </Button>
                <Button asChild variant="ghost">
                  <a href={episodeVideoUrl(episodeId)} download>
                    <Download className="h-4 w-4" /> Télécharger
                  </a>
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 pb-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{children}</span>
    </div>
  )
}
