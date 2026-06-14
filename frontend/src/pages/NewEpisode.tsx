import { useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Sparkles, Wand2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Spinner } from "@/components/studio/states"
import { useCreateEpisode, useProjects } from "@/hooks/use-studio"
import { api } from "@/lib/api"

export function NewEpisode() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const projects = useProjects()
  const createEpisode = useCreateEpisode()

  const [projectId, setProjectId] = useState<number | null>(null)
  const [title, setTitle] = useState("")
  const [prompt, setPrompt] = useState("")
  const [left, setLeft] = useState("Étienne")
  const [right, setRight] = useState("Marc")
  const [leftDesc, setLeftDesc] = useState("")
  const [rightDesc, setRightDesc] = useState("")
  const [draftMode, setDraftMode] = useState(true)
  const [working, setWorking] = useState(false)

  // Default the project once loaded (adjust state during render — runs after all
  // hooks above, so hook order stays stable). Prefer a ?project= query param
  // (e.g. from a project detail page) if it matches a real project.
  if (projectId == null && projects.data && projects.data.length > 0) {
    const requested = Number(searchParams.get("project"))
    const preselect = projects.data.find((p) => p.id === requested)
    setProjectId(preselect ? preselect.id : projects.data[0].id)
  }

  async function submit() {
    if (projectId == null) {
      toast.error("Crée d'abord un projet depuis le dashboard.")
      return
    }
    if (!title.trim() || !prompt.trim()) {
      toast.error("Titre et prompt de base requis.")
      return
    }
    setWorking(true)
    try {
      const ep = await createEpisode.mutateAsync({
        project_id: projectId,
        title: title.trim(),
        draft_mode: draftMode,
      })
      toast.message("Épisode créé", { description: "Génération du script…" })
      await api.generateScript(ep.id, {
        prompt: prompt.trim(),
        char_left_name: left.trim() || "Étienne",
        char_right_name: right.trim() || "Marc",
        char_left_desc: leftDesc.trim(),
        char_right_desc: rightDesc.trim(),
      })
      toast.success("Script généré")
      navigate(`/episodes/${ep.id}/script`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la génération")
    } finally {
      setWorking(false)
    }
  }

  const noProjects = projects.data && projects.data.length === 0

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Nouvel épisode</h1>
        <p className="text-sm text-muted-foreground">
          Décris ton aventure horror POV — le script (3 rounds + épilogue) est généré ensuite.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wand2 className="h-4 w-4 text-primary" /> Brief
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="project">Projet</Label>
            <select
              id="project"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(Number(e.target.value))}
              disabled={noProjects}
              className="flex h-9 w-full rounded-md border border-input bg-background/60 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            >
              {noProjects && <option>Crée un projet dans le dashboard</option>}
              {(projects.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="title">Titre de l'épisode</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Le métro hanté"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="prompt">Prompt de base</Label>
            <Textarea
              id="prompt"
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Deux amis explorent un métro abandonné la nuit et doivent survivre à une présence…"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="left">Personnage gauche — prénom</Label>
              <Input id="left" value={left} onChange={(e) => setLeft(e.target.value)} />
              <Textarea
                id="leftDesc"
                rows={3}
                maxLength={220}
                value={leftDesc}
                onChange={(e) => setLeftDesc(e.target.value)}
                placeholder="Description (optionnel) : apparence + caractère. Ex. « homme à tête d'horloge, gentil mais vicieux »"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="right">Personnage droite — prénom</Label>
              <Input id="right" value={right} onChange={(e) => setRight(e.target.value)} />
              <Textarea
                id="rightDesc"
                rows={3}
                maxLength={220}
                value={rightDesc}
                onChange={(e) => setRightDesc(e.target.value)}
                placeholder="Description (optionnel). Ex. « homme à tête de lune, nerveux mais fidèle ». Vide = l'IA invente."
              />
            </div>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border bg-secondary/30 px-4 py-3">
            <div>
              <p className="text-sm font-medium">Mode brouillon (draft)</p>
              <p className="text-xs text-muted-foreground">
                Assets basse qualité, moins chers, pour itérer vite.
              </p>
            </div>
            <Switch checked={draftMode} onCheckedChange={setDraftMode} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={() => navigate("/")}>
          Annuler
        </Button>
        <Button onClick={submit} disabled={working || noProjects}>
          {working ? <Spinner /> : <Sparkles className="h-4 w-4" />} Générer le script
        </Button>
      </div>
    </div>
  )
}
