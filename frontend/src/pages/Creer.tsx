// /creer — le happy path : choisis un MOULE (format), décris ton idée → le
// PRODUCTEUR cadre le brief → les agents remplissent le moule. Deux moules :
//  • « Horreur — à choix multiple » (CYOA, le flagship) : idée → l'IA remplit la
//    structure fixe (manches, choix, POV) → on atterrit sur la revue de briques.
//  • « Scènes » : idée → table ronde scène par scène → l'atelier.
// La STRUCTURE d'un moule est fixe (code) ; l'IA n'en remplit que le FOND.

import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { ClipboardList, Film, Ghost, Minus, Plus, Sparkles, Wand2 } from "lucide-react"
import { useCreateEpisode, useCreateProject, useProjects } from "@/hooks/use-studio"
import { api } from "@/lib/api"
import type { Brief, Platform, VideoFormat } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/studio/states"

const MIN_UNITS = 1
const MAX_UNITS = 8

const PLATFORMS: { value: Platform; label: string }[] = [
  { value: "tiktok", label: "TikTok" },
  { value: "reels", label: "Reels" },
  { value: "shorts", label: "Shorts" },
  { value: "youtube_short", label: "YouTube Shorts" },
]

// Repli si le catalogue ne charge pas (offline dur) : le flagship d'abord.
const FALLBACK_FORMATS: VideoFormat[] = [
  { id: "aventure", label: "Horreur — à choix multiple",
    tagline: "Un compagnon, des manches, des choix qui peuvent tuer.", description: "" },
  { id: "scenes", label: "Scènes",
    tagline: "Une idée découpée en scènes et plans courts.", description: "" },
]

const FORMAT_ICON: Record<string, typeof Ghost> = { aventure: Ghost, scenes: Film }

export function Creer() {
  const navigate = useNavigate()
  const projects = useProjects()
  const createProject = useCreateProject()
  const createEpisode = useCreateEpisode()
  const [formats, setFormats] = useState<VideoFormat[]>(FALLBACK_FORMATS)
  const [formatId, setFormatId] = useState("aventure")   // le flagship par défaut
  const [title, setTitle] = useState("")
  const [prompt, setPrompt] = useState("")
  const [nUnits, setNUnits] = useState(3)
  const [charLeft, setCharLeft] = useState("")
  const [charRight, setCharRight] = useState("")
  const [brief, setBrief] = useState<Brief | null>(null)
  const [proposing, setProposing] = useState(false)
  const [busy, setBusy] = useState(false)

  const isAventure = formatId === "aventure"

  // Catalogue des moules (GET /api/formats) — non bloquant : on garde le repli.
  useEffect(() => {
    let alive = true
    api.listFormats()
      .then((f) => { if (alive && f.length) setFormats(f) })
      .catch(() => { /* offline : repli déjà en place */ })
    return () => { alive = false }
  }, [])

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
          : "Le producteur a proposé un brief 🎬 — ajuste-le puis lance la création."
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
      // Pas de dead-end pour un premier usage : projet créé à la volée si besoin.
      const project = projects.data?.[0] ?? (await createProject.mutateAsync("Mes vidéos"))
      const ep = await createEpisode.mutateAsync({
        project_id: project.id,
        title: vidTitle,
        draft_mode: true,
        ...(brief ? { brief } : {}),
      })

      if (isAventure) {
        // Le flagship : le moule CYOA est rempli d'un bloc par les agents, puis on
        // révise en briques. Persos laissés vides = l'IA les invente.
        const res = await api.formatDocument(ep.id, {
          prompt: prompt.trim(),
          title: vidTitle,
          format: "aventure",
          options: {
            n_rounds: nUnits,
            ...(charLeft.trim() ? { char_left_name: charLeft.trim() } : {}),
            ...(charRight.trim() ? { char_right_name: charRight.trim() } : {}),
          },
        })
        toast[res.source === "fake" ? "message" : "success"](
          res.source === "fake"
            ? "CYOA de démo — ajoute ta clé OpenAI pour que les agents le remplissent."
            : "Ton horreur à choix multiple est prête 👻 — passe à la revue"
        )
        void navigate(`/editor/${res.id}/review`)
        return
      }

      // Scènes : table ronde scène par scène dans l'atelier.
      const plan = await api.planScenes(ep.id, {
        prompt: prompt.trim(),
        n_scenes: nUnits,
        title: vidTitle,
      })
      toast[plan.source === "fake" ? "message" : "success"](
        plan.source === "fake"
          ? "Arc de démo — ajoute ta clé OpenAI pour une vraie table ronde."
          : "Découpage prêt 🎬 — passe à l'atelier"
      )
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
          Choisis un <strong>format</strong> (moule), décris ton idée : le{" "}
          <strong>producteur</strong> cadre le brief, puis les <strong>agents</strong> remplissent
          le moule — tu révises ensuite.
        </p>
      </div>

      {/* Le MOULE : la structure est fixe, l'IA remplit le fond. */}
      <Card>
        <CardContent className="space-y-3 p-5">
          <Label>Format</Label>
          <div className="grid gap-3 sm:grid-cols-2">
            {formats.map((f) => {
              const Icon = FORMAT_ICON[f.id] ?? Film
              const active = f.id === formatId
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFormatId(f.id)}
                  aria-pressed={active}
                  className={`flex flex-col gap-1 rounded-lg border p-3 text-left transition ${
                    active
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "border-input hover:border-primary/50"
                  }`}
                >
                  <span className="flex items-center gap-2 text-sm font-semibold">
                    <Icon className="h-4 w-4 text-primary" /> {f.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{f.tagline}</span>
                </button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-5 p-5">
          <div className="space-y-2">
            <Label htmlFor="title">Titre</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={isAventure ? "La mine noyée" : "Le métro hanté"}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="idea">Ton idée</Label>
            <Textarea
              id="idea"
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={
                isAventure
                  ? "Deux mineurs coincés dans une galerie inondée ; l'un veut t'aider, l'autre ment…"
                  : "Deux amis explorent un métro abandonné la nuit et doivent survivre à une présence…"
              }
            />
          </div>

          {isAventure && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="charLeft">Compagnon A (optionnel)</Label>
                <Input
                  id="charLeft" value={charLeft} onChange={(e) => setCharLeft(e.target.value)}
                  placeholder="Étienne"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="charRight">Compagnon B (optionnel)</Label>
                <Input
                  id="charRight" value={charRight} onChange={(e) => setCharRight(e.target.value)}
                  placeholder="Marc"
                />
              </div>
              <p className="text-xs text-muted-foreground sm:col-span-2">
                Laisse vide : les agents inventent les deux compagnons à partir de ton idée.
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="units">{isAventure ? "Nombre de manches" : "Nombre de scènes"}</Label>
            <div className="flex items-center rounded-md border border-input bg-background/60 w-fit">
              <Button
                type="button" variant="ghost" size="icon" className="h-9 w-9 rounded-r-none"
                disabled={nUnits <= MIN_UNITS}
                onClick={() => setNUnits((n) => Math.max(MIN_UNITS, n - 1))}
                aria-label="Moins"
              >
                <Minus className="h-4 w-4" />
              </Button>
              <span id="units" className="w-10 text-center text-sm tabular-nums">{nUnits}</span>
              <Button
                type="button" variant="ghost" size="icon" className="h-9 w-9 rounded-l-none"
                disabled={nUnits >= MAX_UNITS}
                onClick={() => setNUnits((n) => Math.min(MAX_UNITS, n + 1))}
                aria-label="Plus"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              {isAventure
                ? "Chaque manche = un lieu, un danger, un choix qui peut être fatal."
                : "Chaque scène = un contexte concentré (une photo d'environnement + des plans courts)."}
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
              ton idée — tu ajustes avant de lancer la création. (Optionnel.)
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
        {busy ? <Spinner /> : <Wand2 className="h-4 w-4" />}
        {isAventure ? "Créer l'horreur à choix multiple" : "Générer les scènes"}
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
