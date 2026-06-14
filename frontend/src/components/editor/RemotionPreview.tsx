// Center preview surface. Wraps the Remotion <Player> with the EditorComposition,
// fed a RenderModel. 9:16 framing matches the studio's .aspect-vertical convention.
// If the model is empty we show a placeholder rather than an empty player.

import { useMemo } from "react"
import { Player } from "@remotion/player"
import { Film } from "lucide-react"
import { EditorComposition } from "./EditorComposition"
import type { RenderModel } from "@/lib/types"

interface RemotionPreviewProps {
  model: RenderModel | undefined
  isLoading?: boolean
}

export function RemotionPreview({ model, isLoading }: RemotionPreviewProps) {
  const fps = model?.canvas.fps ?? 30
  const durationInFrames = useMemo(() => {
    const secs = model?.total_duration ?? 0
    return Math.max(1, Math.round(secs * fps))
  }, [model?.total_duration, fps])

  if (isLoading) {
    return (
      <div className="aspect-vertical h-full max-h-full overflow-hidden rounded-lg border border-border bg-black/60 flex items-center justify-center text-muted-foreground/50">
        <span className="text-xs uppercase tracking-widest">Chargement…</span>
      </div>
    )
  }

  if (!model || model.clips.length === 0) {
    return (
      <div className="aspect-vertical h-full max-h-full overflow-hidden rounded-lg border border-border bg-black/60 flex flex-col items-center justify-center gap-2 text-muted-foreground/50">
        <Film className="h-7 w-7" />
        <span className="text-[10px] uppercase tracking-widest">Aperçu vide</span>
        <span className="text-[10px] text-muted-foreground/40">Ajoute une brique</span>
      </div>
    )
  }

  return (
    <div className="aspect-vertical h-full max-h-full overflow-hidden rounded-lg border border-border bg-black">
      <Player
        component={EditorComposition}
        inputProps={{ model }}
        durationInFrames={durationInFrames}
        fps={fps}
        compositionWidth={model.canvas.width}
        compositionHeight={model.canvas.height}
        style={{ width: "100%", height: "100%" }}
        controls
        loop
        acknowledgeRemotionLicense
      />
    </div>
  )
}
