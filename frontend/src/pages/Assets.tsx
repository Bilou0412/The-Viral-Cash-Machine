import { useMemo, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { RefreshCw, Clapperboard, DollarSign, Wand2, ListChecks, LayoutGrid } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { VerticalPreview } from "@/components/studio/vertical-preview"
import { AssetStatusBadge } from "@/components/studio/status-badge"
import { ErrorState, LoadingState, Spinner } from "@/components/studio/states"
import { ProjectBreadcrumb } from "@/components/studio/project-breadcrumb"
import { AssetReview } from "@/components/studio/asset-review"
import {
  useAssets,
  useBeats,
  useCost,
  useEpisode,
  useGenerateAssets,
  useRegenerateAsset,
} from "@/hooks/use-studio"
import { useJobEvents } from "@/hooks/use-job-events"
import { assetFileUrl } from "@/lib/api"
import { cn, formatCost } from "@/lib/utils"
import { buildDisplayBeats, groupByRound, type DisplayBeat } from "@/lib/beats"
import type { BeatProgress } from "@/hooks/use-job-events"

export function Assets() {
  const { id } = useParams()
  const episodeId = Number(id)
  const episode = useEpisode(episodeId)
  const beats = useBeats(episodeId)
  const assets = useAssets(episodeId)
  const cost = useCost(episodeId)
  const generate = useGenerateAssets(episodeId)
  const regen = useRegenerateAsset(episodeId)
  const progress = useJobEvents(episodeId, episode.data?.status === "assets")
  const [mode, setMode] = useState<"grid" | "review">("grid")

  const displayBeats = useMemo(
    () => buildDisplayBeats(beats.data?.assets ?? [], assets.data ?? []),
    [beats.data, assets.data]
  )
  const rounds = useMemo(() => groupByRound(displayBeats), [displayBeats])

  async function onGenerateAll() {
    try {
      await generate.mutateAsync()
      toast.success("Génération lancée")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec du lancement")
    }
  }

  async function onRegen(assetId: number) {
    try {
      await regen.mutateAsync(assetId)
      toast.success("Régénération lancée")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la régénération")
    }
  }

  if (beats.isLoading) return <LoadingState label="Chargement des beats…" />
  if (beats.isError) return <ErrorState error={beats.error} />

  const overall = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0

  return (
    <div className="space-y-6">
      <ProjectBreadcrumb episodeId={episodeId} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Assets</h1>
          <p className="text-sm text-muted-foreground">
            Image-first : première frame + vidéo par beat. Régénération à l'unité.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost">
            <Link to={`/episodes/${episodeId}/script`}>Script</Link>
          </Button>
          <Button
            variant={mode === "review" ? "default" : "outline"}
            onClick={() => setMode((m) => (m === "review" ? "grid" : "review"))}
          >
            {mode === "review" ? <LayoutGrid className="h-4 w-4" /> : <ListChecks className="h-4 w-4" />}
            {mode === "review" ? "Vue grille" : "Revue"}
          </Button>
          <Button asChild variant="outline">
            <Link to={`/episodes/${episodeId}/montage`}>
              <Clapperboard className="h-4 w-4" /> Montage
            </Link>
          </Button>
          <Button onClick={onGenerateAll} disabled={generate.isPending || progress.active}>
            {generate.isPending || progress.active ? <Spinner /> : <Wand2 className="h-4 w-4" />}
            Générer tout
          </Button>
        </div>
      </div>

      {/* Cost HUD — shown BEFORE generation */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <DollarSign className="h-4 w-4 text-primary" /> Coût estimé
          </CardTitle>
        </CardHeader>
        <CardContent>
          {cost.isLoading ? (
            <Spinner />
          ) : cost.data ? (
            <div className="flex flex-wrap items-center gap-6">
              <div>
                <p className="text-2xl font-bold">{formatCost(cost.data.estimated_usd)}</p>
                <p className="text-xs text-muted-foreground">
                  estimé · réel {formatCost(cost.data.actual_usd)}
                </p>
              </div>
              <div className="flex flex-1 flex-wrap gap-2">
                {cost.data.breakdown.map((b) => (
                  <Badge key={b.model} variant="secondary" className="font-normal">
                    {b.model.split("/").pop()}: {b.units}× {b.unit_kind} = {formatCost(b.amount_usd)}
                  </Badge>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Indisponible</p>
          )}
        </CardContent>
      </Card>

      {progress.active && (
        <Card>
          <CardContent className="flex items-center gap-4 py-4">
            <Spinner />
            <div className="flex-1">
              <p className="mb-1 text-sm">
                Génération en cours… {progress.done}/{progress.total}
              </p>
              <Progress value={overall} />
            </div>
          </CardContent>
        </Card>
      )}

      {assets.isLoading && <LoadingState label="Chargement des assets…" />}

      {mode === "review" ? (
        <AssetReview
          episodeId={episodeId}
          beats={displayBeats}
          onExit={() => setMode("grid")}
        />
      ) : (
        <Tabs defaultValue={String(rounds[0]?.[0] ?? 0)}>
          <TabsList>
            {rounds.map(([idx]) => (
              <TabsTrigger key={idx} value={String(idx)}>
                {idx === -1 ? "Épilogue / Narration" : `Round ${idx + 1}`}
              </TabsTrigger>
            ))}
          </TabsList>
          {rounds.map(([idx, list]) => (
            <TabsContent key={idx} value={String(idx)}>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                {list.map((beat) => (
                  <BeatCard
                    key={beat.key}
                    beat={beat}
                    liveStatus={progress.byGroup[beat.group]}
                    onRegen={onRegen}
                    busy={regen.isPending}
                  />
                ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  )
}

function BeatCard({
  beat,
  liveStatus,
  onRegen,
  busy,
}: {
  beat: DisplayBeat
  liveStatus?: BeatProgress
  onRegen: (assetId: number) => void
  busy: boolean
}) {
  const generating = liveStatus?.status === "generating"
  const hasVideo = !!beat.video && beat.video.status === "ready"
  const hasImage = !!beat.image && beat.image.status === "ready"
  const primary = beat.video ?? beat.image ?? beat.audio
  const isAudioOnly = !beat.image && !beat.video && !!beat.audio
  const excluded = !!primary?.excluded

  return (
    <Card className={cn("overflow-hidden", excluded && "opacity-50")}>
      {!isAudioOnly && (
        <div className="relative">
          <VerticalPreview
            src={hasVideo ? assetFileUrl(beat.video!.id) : hasImage ? assetFileUrl(beat.image!.id) : null}
            kind={hasVideo ? "video" : "image"}
            alt={beat.label}
          />
          <div className="absolute left-1.5 top-1.5">
            <Badge variant={beat.group.startsWith("choice") ? "outline" : "secondary"} className="text-[10px]">
              {beat.label}
            </Badge>
          </div>
          {generating && (
            <div className="absolute inset-x-0 bottom-0 bg-black/70 p-2">
              <Progress value={50} />
            </div>
          )}
        </div>
      )}
      <CardContent className="space-y-2 p-3">
        {isAudioOnly && (
          <Badge variant="secondary" className="text-[10px]">
            {beat.label}
          </Badge>
        )}
        <div className="flex items-center justify-between">
          {primary ? <AssetStatusBadge status={primary.status} /> : (
            <Badge variant="secondary">Non généré</Badge>
          )}
          <div className="flex items-center gap-1">
            {excluded && <Badge variant="destructive" className="text-[10px]">écarté</Badge>}
            {primary?.draft && <Badge variant="warning" className="text-[10px]">draft</Badge>}
          </div>
        </div>

        {beat.text && (
          <p className="line-clamp-2 text-[11px] text-muted-foreground" title={beat.text}>
            {beat.text}
          </p>
        )}

        {beat.audio && beat.audio.status === "ready" && (
          <audio src={assetFileUrl(beat.audio.id)} controls className="h-7 w-full" />
        )}

        {primary && (
          <Button
            size="sm"
            variant="ghost"
            className="h-7 w-full px-2"
            disabled={busy || generating}
            onClick={() => onRegen(primary.id)}
          >
            <RefreshCw className="h-3.5 w-3.5" /> Régénérer
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
