// /creer — le happy path : décris ton idée → le PRODUCTEUR cadre le brief
// (objectif, audience, plateforme, durée, coût) → l'IA découpe en scènes + plans
// courts (photo-first) → on atterrit sur la timeline de revue. Le brief oriente
// toute la chaîne (plateforme/langue/durée pilotent le découpage).

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { ClipboardList, Minus, Plus, Sparkles, Wand2 } from "lucide-react"
import { useCreateEpisode, useCreateProject, useProjects } from "@/hooks/use-studio"
import { api } from "@/lib/api"
import type { Brief, Platform } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/studio/states"

const MIN_SCENES = 1
const MAX_SCENES = 8

const PLATFORMS: { value: Platform; label: string }[] = [
  { value: "tiktok", label: "TikTok" },
  { value: "reels", label: "Reels" },
  { value: "shorts", label: "Shorts" },
  { value: "youtube_short", label: "YouTube Shorts" },
]

export function Creer() {
  const navigate = useNavigate()
  const projects = useProjects()
  const createProject = useCreateProject()
  const createEpisode = useCreateEpisode()
  const [title, setTitle] = useState("")
  const [prompt, setPrompt] = useState("")
  const [nScenes, setNScenes] = useState(3)
  const [brief, setBrief] = useState<Brief | null>(null)
  const [proposing, setProposing] = useState(false)
  const [busy, setBusy] = useState(false)

  const setField = <K extends keyof Brief>(key: K, value: Brief[K]) =>
    setBrief((b) => (b ? { ...b, [key]: value } : b))

  async function onAskProducer() {
    if (!prompt.trim()) {
      toast.error("Décris ton idée de vidéo.")
      return
    }
    setProposing(true)
    try {
      const proposed = await api.proposeBrief({ idea: prompt.trim() })
      setBrief(proposed)
      toast.message(
        proposed.source === "fake"
          ? "Brief de démo — ajoute ta clé OpenAI pour un brief sur mesure."
          : "Le producteur a proposé un brief 🎬 — ajuste-le puis lance les scènes."
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Le producteur n'a pas répondu")
    } finally {
      setProposing(false)
    }
  }

  async function onCreate() {
    if (!prompt.trim()) {
      toast.error("Décris ton idée de vidéo.")
      return
    }
    const vidTitle = title.trim() || "Nouvelle vidéo"
    setBusy(true)
    try {
      // Pas de dead-end pour un premier usage : on crée un projet à la volée s'il
      // n'en existe aucun (Créer est le point d'entrée, pas le Dashboard).
      const project = projects.data?.[0] ?? (await createProject.mutateAsync("Mes vidéos"))
      const ep = await createEpisode.mutateAsync({
        project_id: project.id,
        title: vidTitle,
        draft_mode: true,
        ...(brief ? { brief } : {}),
      })
      // Table ronde : on pose l'ARC (le scénariste), puis on crée scène par scène
      // dans l'atelier (l'équipe discute). Pas de génération d'un bloc.
      const plan = await api.planScenes(ep.id, {
        prompt: prompt.trim(),
        n_scenes: nScenes,
        title: vidTitle,
      })
      if (plan.source === "fake") {
        toast.message("Arc de démo — ajoute ta clé OpenAI pour une vraie table ronde.")
      } else {
        toast.success("Découpage prêt 🎬 — passe à l'atelier")
      }
      void navigate(`/editor/${plan.id}/room`)
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
          Décris ton idée. Le <strong>producteur</strong> cadre le brief, puis l'IA découpe en{" "}
          <strong>scènes</strong> et <strong>plans courts</strong> — tu ajustes ensuite sur la
          timeline.
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
        </CardContent>
      </Card>

      {/* Phase développement : le producteur cadre le brief (l'humain édite). */}
      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <ClipboardList className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-semibold">Producteur — le brief</h2>
            </div>
            <Button
              type="button" variant="outline" size="sm" className="gap-1.5"
              onClick={onAskProducer} disabled={proposing || !prompt.trim()}
            >
              {proposing ? <Spinner /> : <ClipboardList className="h-3.5 w-3.5" />}
              {brief ? "Re-proposer" : "Demander au producteur"}
            </Button>
          </div>

          {!brief ? (
            <p className="text-sm text-muted-foreground">
              Le producteur propose objectif, audience, plateforme, durée et ton à partir de
              ton idée — tu ajustes avant de lancer les scènes. (Optionnel : tu peux générer
              sans brief.)
            </p>
          ) : (
            <div className="space-y-3">
              <BriefField label="Objectif">
                <Input value={brief.objectif} onChange={(e) => setField("objectif", e.target.value)} />
              </BriefField>
              <BriefField label="Audience">
                <Input value={brief.audience} onChange={(e) => setField("audience", e.target.value)} />
              </BriefField>
              <div className="grid gap-3 sm:grid-cols-3">
                <BriefField label="Plateforme">
                  <select
                    value={brief.plateforme}
                    onChange={(e) => setField("plateforme", e.target.value as Platform)}
                    className="h-9 w-full rounded-md border border-input bg-background/60 px-2 text-sm"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </BriefField>
                <BriefField label="Durée (s)">
                  <Input
                    type="number" min={5} value={brief.duree_s}
                    onChange={(e) => setField("duree_s", Number(e.target.value) || 0)}
                  />
                </BriefField>
                <BriefField label="Budget ($)">
                  <Input
                    type="number" min={0} value={brief.budget_usd}
                    onChange={(e) => setField("budget_usd", Number(e.target.value) || 0)}
                  />
                </BriefField>
              </div>
              <BriefField label="Ton">
                <Input value={brief.ton} onChange={(e) => setField("ton", e.target.value)} />
              </BriefField>
            </div>
          )}
        </CardContent>
      </Card>

      <Button onClick={onCreate} disabled={busy} className="w-full gap-2">
        {busy ? <Spinner /> : <Wand2 className="h-4 w-4" />} Générer les scènes
      </Button>
    </div>
  )
}

function BriefField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  )
}
