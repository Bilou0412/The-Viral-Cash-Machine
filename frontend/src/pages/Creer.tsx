// /creer — le happy path : décris ton idée → l'IA découpe en scènes + plans
// courts (photo-first) → on atterrit sur la timeline de revue. (Phase 1 : Fake
// offline sans clé ; la vraie IA arrive en Phase 3.)

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Minus, Plus, Sparkles, Wand2 } from "lucide-react"
import { useCreateEpisode, useProjects } from "@/hooks/use-studio"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/studio/states"

const MIN_SCENES = 1
const MAX_SCENES = 8

export function Creer() {
  const navigate = useNavigate()
  const projects = useProjects()
  const createEpisode = useCreateEpisode()
  const [title, setTitle] = useState("")
  const [prompt, setPrompt] = useState("")
  const [nScenes, setNScenes] = useState(3)
  const [busy, setBusy] = useState(false)

  async function onCreate() {
    if (!prompt.trim()) {
      toast.error("Décris ton idée de vidéo.")
      return
    }
    const project = projects.data?.[0]
    if (!project) {
      toast.error("Crée d'abord un projet depuis le dashboard.")
      return
    }
    const vidTitle = title.trim() || "Nouvelle vidéo"
    setBusy(true)
    try {
      const ep = await createEpisode.mutateAsync({
        project_id: project.id,
        title: vidTitle,
        draft_mode: true,
      })
      const doc = await api.createSceneDocument(ep.id, {
        prompt: prompt.trim(),
        n_scenes: nScenes,
        title: vidTitle,
      })
      if (doc.source === "fake") {
        toast.warning("Scènes de démo — ajoute ta clé OpenAI dans Réglages pour du vrai contenu.")
      } else {
        toast.success("Scènes générées 🎬")
      }
      void navigate(`/editor/${doc.id}/review`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Génération impossible")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
          <Sparkles className="h-6 w-6 text-primary" /> Créer une vidéo
        </h1>
        <p className="text-sm text-muted-foreground">
          Décris ton idée. L'IA la découpe en <strong>scènes</strong> puis en{" "}
          <strong>plans courts</strong> (photo d'environnement + mouvement + son) — tu ajustes
          ensuite sur la timeline.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-5 p-5">
          <div className="space-y-2">
            <Label htmlFor="title">Titre</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Le métro hanté"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="idea">Ton idée</Label>
            <Textarea
              id="idea"
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Deux amis explorent un métro abandonné la nuit et doivent survivre à une présence…"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="scenes">Nombre de scènes</Label>
            <div className="flex items-center rounded-md border border-input bg-background/60 w-fit">
              <Button
                type="button" variant="ghost" size="icon" className="h-9 w-9 rounded-r-none"
                disabled={nScenes <= MIN_SCENES}
                onClick={() => setNScenes((n) => Math.max(MIN_SCENES, n - 1))}
                aria-label="Moins de scènes"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <span id="scenes" className="w-10 text-center text-sm tabular-nums">{nScenes}</span>
              <Button
                type="button" variant="ghost" size="icon" className="h-9 w-9 rounded-l-none"
                disabled={nScenes >= MAX_SCENES}
                onClick={() => setNScenes((n) => Math.min(MAX_SCENES, n + 1))}
                aria-label="Plus de scènes"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Chaque scène = un contexte concentré (une photo d'environnement + des plans courts).
            </p>
          </div>

          <Button onClick={onCreate} disabled={busy} className="w-full gap-2">
            {busy ? <Spinner /> : <Wand2 className="h-4 w-4" />} Générer les scènes
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
