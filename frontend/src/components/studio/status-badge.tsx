import { Badge } from "@/components/ui/badge"
import type { AssetStatus, EpisodeStatus } from "@/lib/types"

const EPISODE: Record<EpisodeStatus, { label: string; variant: Parameters<typeof Badge>[0]["variant"] }> = {
  draft: { label: "Brouillon", variant: "secondary" },
  assets: { label: "Assets", variant: "accent" },
  montage: { label: "Montage", variant: "warning" },
  done: { label: "Final", variant: "success" },
}

const ASSET: Record<AssetStatus, { label: string; variant: Parameters<typeof Badge>[0]["variant"] }> = {
  pending: { label: "En attente", variant: "secondary" },
  generating: { label: "Génération", variant: "warning" },
  ready: { label: "Prêt", variant: "success" },
  failed: { label: "Erreur", variant: "destructive" },
  error: { label: "Erreur", variant: "destructive" },
}

export function EpisodeStatusBadge({ status }: { status: EpisodeStatus }) {
  const s = EPISODE[status] ?? EPISODE.draft
  return <Badge variant={s.variant}>{s.label}</Badge>
}

export function AssetStatusBadge({ status }: { status: AssetStatus }) {
  const s = ASSET[status] ?? ASSET.pending
  return <Badge variant={s.variant}>{s.label}</Badge>
}
