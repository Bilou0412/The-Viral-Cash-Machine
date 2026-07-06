// Phase Distribution : l'attaché de presse / Growth écrit la fiche de sortie
// (titre, description, hashtags, hook). Le producteur édite et « dirige » l'agent
// (régénère), puis télécharge la vidéo.

import { useState } from "react"
import { toast } from "sonner"
import { Download, Megaphone, RefreshCw } from "lucide-react"
import {
  useDistribution,
  useGenerateDistribution,
  useSaveDistribution,
} from "@/hooks/use-editor"
import { editorVideoUrl } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import type { DistributionKit } from "@/lib/types"

const EMPTY: DistributionKit = { title: "", description: "", hashtags: [], hook: "" }

export function DistributionPanel({ docId }: { docId: string }) {
  const existing = useDistribution(docId)
  const generate = useGenerateDistribution(docId)
  const save = useSaveDistribution(docId)
  // Édition locale du producteur ; à défaut on affiche la fiche du serveur.
  const [edited, setEdited] = useState<DistributionKit | null>(null)

  const server = existing.data ?? generate.data
  const serverKit: DistributionKit | null = server
    ? { title: server.title, description: server.description, hashtags: server.hashtags, hook: server.hook }
    : null
  const kit = edited ?? serverKit

  const busy = generate.isPending || existing.isLoading
  const draft = kit ?? EMPTY
  const set = (patch: Partial<DistributionKit>) => setEdited({ ...draft, ...patch })

  const onDirect = () =>
    generate.mutate(undefined, {
      onSuccess: (k) => {
        setEdited(null) // laisse la nouvelle fiche du serveur s'afficher
        toast.success(k.source === "fake" ? "Fiche de démo — ajoute ta clé OpenAI" : "Fiche écrite 📣")
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "Échec de l'attaché de presse"),
    })

  const onSave = () =>
    save.mutate(draft, { onSuccess: () => toast.success("Fiche enregistrée") })

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Megaphone className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">Attaché de presse — fiche de sortie</h3>
        </div>
        <Button variant="outline" size="sm" onClick={onDirect} disabled={busy} className="gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          {kit ? "Diriger l'attaché de presse" : "Rédiger la fiche"}
        </Button>
      </div>

      {!kit ? (
        <p className="text-sm text-muted-foreground">
          L'attaché de presse écrit le titre, la description, les hashtags et le hook de ta
          vidéo. Clique « Rédiger la fiche » pour le lancer.
        </p>
      ) : (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Titre</label>
            <Input value={draft.title} onChange={(e) => set({ title: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Hook (1re phrase)</label>
            <Input value={draft.hook} onChange={(e) => set({ hook: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Description</label>
            <Textarea rows={3} value={draft.description} onChange={(e) => set({ description: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Hashtags</label>
            <Input
              value={draft.hashtags.join(" ")}
              onChange={(e) => set({ hashtags: e.target.value.split(/\s+/).filter(Boolean) })}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={onSave} disabled={save.isPending}>
              Enregistrer la fiche
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <a href={editorVideoUrl(docId)} download>
                <Download className="h-3.5 w-3.5" /> Télécharger la vidéo
              </a>
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
