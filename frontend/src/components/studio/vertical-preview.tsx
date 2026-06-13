import { Film, ImageOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface VerticalPreviewProps {
  src?: string | null
  kind?: "image" | "video"
  alt?: string
  className?: string
  poster?: string | null
  controls?: boolean
}

/** A 9:16 media frame — the canonical preview surface of the studio. */
export function VerticalPreview({
  src,
  kind = "image",
  alt,
  className,
  poster,
  controls = false,
}: VerticalPreviewProps) {
  return (
    <div
      className={cn(
        "aspect-vertical w-full overflow-hidden rounded-md border border-border bg-black/60 relative",
        className
      )}
    >
      {src ? (
        kind === "video" ? (
          <video
            src={src}
            poster={poster ?? undefined}
            controls={controls}
            playsInline
            muted={!controls}
            loop={!controls}
            className="h-full w-full object-cover"
          />
        ) : (
          <img src={src} alt={alt ?? ""} className="h-full w-full object-cover" />
        )
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-muted-foreground/50">
          {kind === "video" ? <Film className="h-7 w-7" /> : <ImageOff className="h-7 w-7" />}
          <span className="text-[10px] uppercase tracking-widest">9:16</span>
        </div>
      )}
    </div>
  )
}
