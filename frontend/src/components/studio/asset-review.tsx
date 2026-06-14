// Step-by-step asset review (LOT 2 / M1): walk the beats one at a time with a
// full 9:16 preview + prompt, and per-asset actions (valider / régénérer /
// éditer le prompt / écarter). A final récap step lists kept vs écarté counts
// and surfaces the existing montage/produce actions.

import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  Pencil,
  RefreshCw,
  RotateCcw,
  Trash2,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { VerticalPreview } from "@/components/studio/vertical-preview"
import { AssetStatusBadge } from "@/components/studio/status-badge"
import { Spinner } from "@/components/studio/states"
import { assetFileUrl } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { DisplayBeat } from "@/lib/beats"
import type { Asset } from "@/lib/types"
import { useRegenerateAsset, useUpdateAsset } from "@/hooks/use-studio"

/** The asset we let the user act on for a given beat (video > image > audio). */
function primaryAsset(beat: DisplayBeat): Asset | undefined {
  return beat.video ?? beat.image ?? beat.audio
}

function previewSrcFor(beat: DisplayBeat): { src: string | null; kind: "image" | "video" } {
  if (beat.video && beat.video.status === "ready")
    return { src: assetFileUrl(beat.video.id), kind: "video" }
  if (beat.image && beat.image.status === "ready")
    return { src: assetFileUrl(beat.image.id), kind: "image" }
  return { src: null, kind: beat.video ? "video" : "image" }
}

export function AssetReview({
  episodeId,
  beats,
  onExit,
}: {
  episodeId: number
  beats: DisplayBeat[]
  onExit: () => void
}) {
  const total = beats.length
  const [index, setIndex] = useState(0)
  const [reviewed, setReviewed] = useState<Set<string>>(new Set())
  const [showRecap, setShowRecap] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draftPrompt, setDraftPrompt] = useState("")

  const regen = useRegenerateAsset(episodeId)
  const updateAsset = useUpdateAsset(episodeId)

  const counts = useMemo(() => {
    let kept = 0
    let excluded = 0
    for (const b of beats) {
      const a = primaryAsset(b)
      if (a?.excluded) excluded += 1
      else kept += 1
    }
    return { kept, excluded }
  }, [beats])

  if (total === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Aucun beat à passer en revue.
        </CardContent>
      </Card>
    )
  }

  if (showRecap) {
    return (
      <RecapStep
        episodeId={episodeId}
        beats={beats}
        kept={counts.kept}
        excluded={counts.excluded}
        onBack={() => setShowRecap(false)}
      />
    )
  }

  const safeIndex = Math.min(index, total - 1)
  const beat = beats[safeIndex]
  const asset = primaryAsset(beat)
  const { src, kind } = previewSrcFor(beat)
  const excluded = !!asset?.excluded
  const isReviewed = reviewed.has(beat.key)
  const busy = regen.isPending || updateAsset.isPending

  const promptText = beat.framePrompt ?? beat.motionPrompt ?? beat.text ?? asset?.prompt ?? ""

  function markReviewed() {
    setReviewed((prev) => {
      const next = new Set(prev)
      next.add(beat.key)
      return next
    })
  }

  function goNext() {
    setEditing(false)
    if (safeIndex >= total - 1) {
      setShowRecap(true)
    } else {
      setIndex(safeIndex + 1)
    }
  }

  function goPrev() {
    setEditing(false)
    setIndex(Math.max(0, safeIndex - 1))
  }

  function onValidate() {
    markReviewed()
    goNext()
  }

  async function onRegen() {
    if (!asset) return
    try {
      await regen.mutateAsync(asset.id)
      toast.success("Régénération lancée")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la régénération")
    }
  }

  function onStartEdit() {
    setDraftPrompt(promptText)
    setEditing(true)
  }

  async function onSavePrompt(thenRegen: boolean) {
    if (!asset) return
    try {
      await updateAsset.mutateAsync({ assetId: asset.id, body: { prompt: draftPrompt } })
      setEditing(false)
      toast.success("Prompt mis à jour")
      if (thenRegen) {
        await regen.mutateAsync(asset.id)
        toast.success("Régénération lancée")
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la mise à jour")
    }
  }

  async function onToggleExcluded() {
    if (!asset) return
    try {
      const updated = await updateAsset.mutateAsync({
        assetId: asset.id,
        body: { excluded: !asset.excluded },
      })
      toast.message(updated.excluded ? "Écarté du montage" : "Réintégré au montage")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de l'action")
    }
  }

  return (
    <div className="space-y-4">
      {/* Position indicator + exit */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="tabular-nums">
            {safeIndex + 1} / {total}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {beat.roundIndex == null ? "Épilogue / Narration" : `Round ${beat.roundIndex + 1}`} ·{" "}
            <span className="text-foreground">{beat.label}</span>
          </span>
          {isReviewed && (
            <Badge variant="success" className="text-[10px]">
              <Check className="mr-1 h-3 w-3" /> validé
            </Badge>
          )}
          {excluded && (
            <Badge variant="destructive" className="text-[10px]">
              écarté
            </Badge>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={onExit}>
          Quitter la revue
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-[300px_1fr]">
        {/* Full 9:16 preview */}
        <div className={cn("transition-opacity", excluded && "opacity-40")}>
          <VerticalPreview src={src} kind={kind} alt={beat.label} controls />
          <div className="mt-2 flex items-center justify-between">
            {asset ? <AssetStatusBadge status={asset.status} /> : <Badge variant="secondary">Non généré</Badge>}
            {asset?.draft && <Badge variant="warning" className="text-[10px]">draft</Badge>}
          </div>
          {beat.audio && beat.audio.status === "ready" && (
            <audio src={assetFileUrl(beat.audio.id)} controls className="mt-2 h-8 w-full" />
          )}
        </div>

        {/* Prompt + actions */}
        <Card>
          <CardContent className="space-y-4 p-4">
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {beat.text != null && beat.framePrompt == null ? "Texte" : "Prompt"}
              </p>
              {editing ? (
                <div className="space-y-2">
                  <Textarea
                    rows={6}
                    value={draftPrompt}
                    onChange={(e) => setDraftPrompt(e.target.value)}
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <Button size="sm" disabled={busy} onClick={() => onSavePrompt(false)}>
                      {updateAsset.isPending ? <Spinner /> : <Check className="h-4 w-4" />} Enregistrer
                    </Button>
                    <Button size="sm" variant="outline" disabled={busy} onClick={() => onSavePrompt(true)}>
                      <RefreshCw className="h-4 w-4" /> Enregistrer + régénérer
                    </Button>
                    <Button size="sm" variant="ghost" disabled={busy} onClick={() => setEditing(false)}>
                      Annuler
                    </Button>
                  </div>
                </div>
              ) : (
                <p className="whitespace-pre-wrap rounded-md border border-border bg-secondary/20 p-3 text-sm text-muted-foreground">
                  {promptText || "—"}
                </p>
              )}
            </div>

            {!editing && (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" onClick={onValidate} disabled={busy}>
                  <Check className="h-4 w-4" /> Valider
                </Button>
                <Button size="sm" variant="outline" onClick={onRegen} disabled={busy || !asset}>
                  {regen.isPending ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Régénérer
                </Button>
                <Button size="sm" variant="outline" onClick={onStartEdit} disabled={busy || !asset}>
                  <Pencil className="h-4 w-4" /> Éditer le prompt
                </Button>
                {excluded ? (
                  <Button size="sm" variant="outline" onClick={onToggleExcluded} disabled={busy || !asset}>
                    <RotateCcw className="h-4 w-4" /> Garder
                  </Button>
                ) : (
                  <Button size="sm" variant="destructive" onClick={onToggleExcluded} disabled={busy || !asset}>
                    <Trash2 className="h-4 w-4" /> Écarter
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Nav */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={goPrev} disabled={safeIndex === 0}>
          <ChevronLeft className="h-4 w-4" /> Précédent
        </Button>
        <Button variant="outline" onClick={() => setShowRecap(true)}>
          <Clapperboard className="h-4 w-4" /> Récap & montage
        </Button>
        <Button onClick={goNext}>
          {safeIndex >= total - 1 ? "Terminer" : "Suivant"} <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Quick reference link back to the grid */}
      <p className="text-center text-xs text-muted-foreground">
        Astuce : <Link to={`/episodes/${episodeId}/assets`} className="underline">vue grille</Link> pour
        une vue d'ensemble.
      </p>
    </div>
  )
}

function RecapStep({
  episodeId,
  beats,
  kept,
  excluded,
  onBack,
}: {
  episodeId: number
  beats: DisplayBeat[]
  kept: number
  excluded: number
  onBack: () => void
}) {
  // Group beats by round for a compact recap list.
  const byRound = useMemo(() => {
    const groups = new Map<number, DisplayBeat[]>()
    for (const b of beats) {
      const bucket = b.roundIndex ?? -1
      const list = groups.get(bucket) ?? []
      list.push(b)
      groups.set(bucket, list)
    }
    return [...groups.entries()].sort((a, b) => a[0] - b[0])
  }, [beats])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Récapitulatif</h2>
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ChevronLeft className="h-4 w-4" /> Revenir à la revue
        </Button>
      </div>

      <div className="flex flex-wrap gap-3">
        <Badge variant="success" className="px-3 py-1 text-sm">
          {kept} conservé{kept > 1 ? "s" : ""}
        </Badge>
        <Badge variant="destructive" className="px-3 py-1 text-sm">
          {excluded} écarté{excluded > 1 ? "s" : ""}
        </Badge>
      </div>

      <Card>
        <CardContent className="divide-y divide-border/60 p-0">
          {byRound.map(([bucket, list]) => (
            <div key={bucket} className="px-4 py-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {bucket === -1 ? "Épilogue / Narration" : `Round ${bucket + 1}`}
              </p>
              <div className="flex flex-wrap gap-2">
                {list.map((b) => {
                  const a = b.video ?? b.image ?? b.audio
                  const isExcluded = !!a?.excluded
                  return (
                    <Badge
                      key={b.key}
                      variant={isExcluded ? "destructive" : "secondary"}
                      className={cn("font-normal", isExcluded && "line-through opacity-70")}
                    >
                      {b.label}
                    </Badge>
                  )
                })}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="flex flex-wrap justify-end gap-2">
        <Button asChild variant="outline">
          <Link to={`/episodes/${episodeId}/montage`}>
            <Clapperboard className="h-4 w-4" /> Aller au montage
          </Link>
        </Button>
        <Button asChild>
          <Link to={`/episodes/${episodeId}/montage`}>Produire la vidéo</Link>
        </Button>
      </div>
    </div>
  )
}
