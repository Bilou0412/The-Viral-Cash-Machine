// Remotion composition that renders a RenderModel. Each clip becomes a Sequence
// positioned by start/duration (converted to frames via fps). Media kinds map to
// <Img>/<OffthreadVideo>/<Audio>/text overlay. Kept intentionally simple — this
// is a preview, not the final FFmpeg render (that happens server-side).

import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence } from "remotion"
import type { RenderClip, RenderModel } from "@/lib/types"

export interface EditorCompositionProps {
  model: RenderModel
}

function ClipLayer({ clip, fps }: { clip: RenderClip; fps: number }) {
  const z = clip.z ?? clip.track ?? 0
  const base: React.CSSProperties = { zIndex: z }

  if (clip.media === "audio") {
    return clip.src ? <Audio src={clip.src} /> : null
  }
  if (clip.media === "video") {
    return clip.src ? (
      <AbsoluteFill style={base}>
        <OffthreadVideo src={clip.src} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
    ) : null
  }
  if (clip.media === "image" || clip.media === "overlay") {
    return clip.src ? (
      <AbsoluteFill style={base}>
        <Img src={clip.src} style={{ width: "100%", height: "100%", objectFit: clip.media === "overlay" ? "contain" : "cover" }} />
      </AbsoluteFill>
    ) : null
  }
  // text
  return (
    <AbsoluteFill
      style={{
        ...base,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        padding: "0 8% 14%",
      }}
    >
      <span
        style={{
          color: "white",
          fontFamily: "Inter, sans-serif",
          fontWeight: 700,
          fontSize: Math.round(fps > 0 ? 64 : 64),
          textAlign: "center",
          textShadow: "0 2px 12px rgba(0,0,0,0.9)",
          lineHeight: 1.1,
        }}
      >
        {clip.text ?? ""}
      </span>
    </AbsoluteFill>
  )
}

export function EditorComposition({ model }: EditorCompositionProps) {
  const { fps } = model.canvas
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {model.clips.map((clip) => {
        const from = Math.round(clip.start * fps)
        const durationInFrames = Math.max(1, Math.round(clip.duration * fps))
        return (
          <Sequence key={clip.id} from={from} durationInFrames={durationInFrames}>
            <ClipLayer clip={clip} fps={fps} />
          </Sequence>
        )
      })}
    </AbsoluteFill>
  )
}
