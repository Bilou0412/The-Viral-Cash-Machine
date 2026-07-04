import { useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Save, Boxes, RefreshCw, Skull, SlidersHorizontal } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { ErrorState, LoadingState, Spinner } from "@/components/studio/states"
import { ProjectBreadcrumb } from "@/components/studio/project-breadcrumb"
import { useGenerateScript, useSaveScript, useScript } from "@/hooks/use-studio"
import type { AdventureScript, Choice, Round } from "@/lib/types"

export function ScriptEditor() {
  const { id } = useParams()
  const episodeId = Number(id)
  const navigate = useNavigate()
  const scriptQuery = useScript(episodeId)
  const saveScript = useSaveScript(episodeId)
  const regen = useGenerateScript(episodeId)

  const [draft, setDraft] = useState<AdventureScript | null>(null)
  const [loadedFor, setLoadedFor] = useState<number | null>(null)
  const [dirty, setDirty] = useState(false)
  const [regenOpen, setRegenOpen] = useState(false)
  const [regenPrompt, setRegenPrompt] = useState("")
  const [reviewing, setReviewing] = useState(false)

  // Initialize the editable copy during render when fresh data arrives for this
  // episode (React-recommended "adjust state while rendering" pattern).
  if (scriptQuery.data && loadedFor !== episodeId) {
    setDraft(scriptQuery.data)
    setLoadedFor(episodeId)
    setDirty(false)
  }

  if (scriptQuery.isLoading) return <LoadingState label="Chargement du script…" />
  if (scriptQuery.isError) return <ErrorState error={scriptQuery.error} />
  if (!draft) return <LoadingState />

  function update(patch: Partial<AdventureScript>) {
    setDraft((d) => (d ? { ...d, ...patch } : d))
    setDirty(true)
  }
  function updateRound(idx: number, patch: Partial<Round>) {
    setDraft((d) => {
      if (!d) return d
      const rounds = [...d.rounds] as [Round, Round, Round]
      const current = rounds[idx]
      if (!current) return d
      rounds[idx] = { ...current, ...patch }
      return { ...d, rounds }
    })
    setDirty(true)
  }
  function updateChoice(rIdx: number, cIdx: 0 | 1, patch: Partial<Choice>) {
    setDraft((d) => {
      if (!d) return d
      const rounds = [...d.rounds] as [Round, Round, Round]
      const round = rounds[rIdx]
      if (!round) return d
      const choices = [...round.choices] as [Choice, Choice]
      const current = choices[cIdx]
      if (!current) return d
      choices[cIdx] = { ...current, ...patch }
      rounds[rIdx] = { ...round, choices }
      return { ...d, rounds }
    })
    setDirty(true)
  }

  async function save() {
    if (!draft) return
    try {
      await saveScript.mutateAsync(draft)
      setDirty(false)
      toast.success("Script sauvegardé")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la sauvegarde")
    }
  }

  async function regenerate() {
    if (!regenPrompt.trim() || !draft) return
    try {
      const s = await regen.mutateAsync({
        prompt: regenPrompt.trim(),
        char_left_name: draft.char_left_name,
        char_right_name: draft.char_right_name,
      })
      setDraft(s)
      setDirty(false)
      setRegenOpen(false)
      setRegenPrompt("")
      toast.success("Script régénéré")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de la régénération")
    }
  }

  async function goToAssets() {
    if (dirty) await save()
    void navigate(`/episodes/${episodeId}/assets`)
  }

  async function goToReview() {
    if (dirty) await save()
    setReviewing(true)
    try {
      // Matérialise le script en document de briques puis ouvre la revue.
      const doc = await api.reviewFromScript(episodeId)
      void navigate(`/editor/${doc.id}/review`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Impossible d'ouvrir la revue")
    } finally {
      setReviewing(false)
    }
  }

  return (
    <div className="space-y-6">
      <ProjectBreadcrumb episodeId={episodeId} />
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Script & Casting</h1>
          <p className="text-sm text-muted-foreground">
            3 rounds à dilemme + épilogue. Visuels en anglais, dialogues en français.
          </p>
        </div>
        <div className="flex gap-2">
          <Dialog open={regenOpen} onOpenChange={setRegenOpen}>
            <DialogTrigger asChild>
              <Button variant="ghost">
                <RefreshCw className="h-4 w-4" /> Régénérer
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Régénérer le script</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-muted-foreground">
                Nouveau prompt de base. Les prénoms ({draft.char_left_name} /{" "}
                {draft.char_right_name}) sont conservés. Cela remplace le script actuel.
              </p>
              <Textarea
                rows={4}
                value={regenPrompt}
                onChange={(e) => setRegenPrompt(e.target.value)}
                placeholder="Deux amis explorent une mine abandonnée…"
              />
              <DialogFooter>
                <Button onClick={regenerate} disabled={regen.isPending || !regenPrompt.trim()}>
                  {regen.isPending ? <Spinner /> : <RefreshCw className="h-4 w-4" />} Régénérer
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Button variant="outline" onClick={save} disabled={saveScript.isPending || !dirty}>
            {saveScript.isPending ? <Spinner /> : <Save className="h-4 w-4" />} Sauvegarder
          </Button>
          <Button variant="outline" onClick={goToReview} disabled={reviewing}>
            {reviewing ? <Spinner /> : <SlidersHorizontal className="h-4 w-4" />} Réviser en briques
          </Button>
          <Button onClick={goToAssets}>
            <Boxes className="h-4 w-4" /> Générer les assets
          </Button>
        </div>
      </div>

      {/* Casting */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Casting</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-2">
          {(["left", "right"] as const).map((side) => {
            const nameKey = side === "left" ? "char_left_name" : "char_right_name"
            const descKey = side === "left" ? "char_left_desc" : "char_right_desc"
            const voiceKey = side === "left" ? "char_left_voice" : "char_right_voice"
            return (
              <div key={side} className="space-y-3 rounded-lg border border-border bg-secondary/20 p-4">
                <Badge variant={side === "left" ? "default" : "accent"}>
                  Personnage {side === "left" ? "gauche" : "droite"}
                </Badge>
                <Field label="Prénom (FR)">
                  <Input value={draft[nameKey]} onChange={(e) => update({ [nameKey]: e.target.value })} />
                </Field>
                <Field label="Apparence (EN)">
                  <Textarea
                    rows={2}
                    value={draft[descKey]}
                    onChange={(e) => update({ [descKey]: e.target.value })}
                  />
                </Field>
                <Field label="Voix (EN)">
                  <Input
                    value={draft[voiceKey].description}
                    onChange={(e) => update({ [voiceKey]: { description: e.target.value } })}
                  />
                </Field>
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Rounds */}
      <Tabs defaultValue="0">
        <TabsList>
          {draft.rounds.map((_, i) => (
            <TabsTrigger key={i} value={String(i)}>
              Round {i + 1}
            </TabsTrigger>
          ))}
          <TabsTrigger value="epilogue">Épilogue</TabsTrigger>
        </TabsList>

        {draft.rounds.map((round, i) => (
          <TabsContent key={i} value={String(i)}>
            <RoundCard
              round={round}
              onRound={(p) => updateRound(i, p)}
              onChoice={(c, p) => updateChoice(i, c, p)}
            />
          </TabsContent>
        ))}

        <TabsContent value="epilogue">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Épilogue & transition</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="Narration transition (FR)">
                <Textarea
                  rows={2}
                  value={draft.transition_narration_fr}
                  onChange={(e) => update({ transition_narration_fr: e.target.value })}
                />
              </Field>
              <Field label="Autre chemin — visuel (EN)">
                <Textarea
                  rows={2}
                  value={draft.epilogue_other_desc}
                  onChange={(e) => update({ epilogue_other_desc: e.target.value })}
                />
              </Field>
              <Field label="Narration épilogue (FR)">
                <Textarea
                  rows={2}
                  value={draft.epilogue_narration_fr}
                  onChange={(e) => update({ epilogue_narration_fr: e.target.value })}
                />
              </Field>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function RoundCard({
  round,
  onRound,
  onChoice,
}: {
  round: Round
  onRound: (p: Partial<Round>) => void
  onChoice: (c: 0 | 1, p: Partial<Choice>) => void
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
            Action & environnement
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Field label="Action (EN)">
            <Input value={round.action_desc} onChange={(e) => onRound({ action_desc: e.target.value })} />
          </Field>
          <Field label="Narration action (FR)">
            <Input
              value={round.action_narration_fr}
              onChange={(e) => onRound({ action_narration_fr: e.target.value })}
            />
          </Field>
          <Field label="Environnement (EN)">
            <Input
              value={round.environment_desc}
              onChange={(e) => onRound({ environment_desc: e.target.value })}
            />
          </Field>
          <Field label="Danger (EN)">
            <Input value={round.danger_desc} onChange={(e) => onRound({ danger_desc: e.target.value })} />
          </Field>
          <Field label="Narration environnement (FR)">
            <Input
              value={round.environment_narration_fr}
              onChange={(e) => onRound({ environment_narration_fr: e.target.value })}
            />
          </Field>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
            Réplique & dilemme
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Field label="Réplique face-cam (FR)">
            <Input
              value={round.character_line_fr}
              onChange={(e) => onRound({ character_line_fr: e.target.value })}
            />
          </Field>
          <Field label="Manière / delivery (EN)">
            <Input
              value={round.character_delivery}
              onChange={(e) => onRound({ character_delivery: e.target.value })}
            />
          </Field>
          <Field label="Narration des choix (FR)">
            <Input
              value={round.choice_narration_fr}
              onChange={(e) => onRound({ choice_narration_fr: e.target.value })}
            />
          </Field>
          {([0, 1] as const).map((c) => (
            <div key={c} className="rounded-md border border-border bg-secondary/20 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium">Choix {c === 0 ? "A" : "B"}</span>
                {round.choices[c].is_fatal && (
                  <Badge variant="destructive" className="gap-1">
                    <Skull className="h-3 w-3" /> Fatal
                  </Badge>
                )}
              </div>
              <Input
                value={round.choices[c].label_fr}
                onChange={(e) => onChoice(c, { label_fr: e.target.value })}
                placeholder="Label (FR)"
              />
              <Input
                value={round.choices[c].image_desc}
                onChange={(e) => onChoice(c, { image_desc: e.target.value })}
                placeholder="Visuel (EN)"
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-sm uppercase tracking-wide text-muted-foreground">
            Issues
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-3">
            <Badge variant="destructive">Issue fatale</Badge>
            <Field label="Kill (EN)">
              <Input value={round.fatal_kill_desc} onChange={(e) => onRound({ fatal_kill_desc: e.target.value })} />
            </Field>
            <Field label="Réaction POV (EN)">
              <Input
                value={round.fatal_pov_reaction}
                onChange={(e) => onRound({ fatal_pov_reaction: e.target.value })}
              />
            </Field>
            <Field label="Narration (FR)">
              <Input
                value={round.fatal_narration_fr}
                onChange={(e) => onRound({ fatal_narration_fr: e.target.value })}
              />
            </Field>
          </div>
          <div className="space-y-3">
            <Badge variant="success">Survie</Badge>
            <Field label="Issue (EN)">
              <Input
                value={round.survival_outcome_desc}
                onChange={(e) => onRound({ survival_outcome_desc: e.target.value })}
              />
            </Field>
            <Field label="Narration (FR)">
              <Input
                value={round.survival_narration_fr}
                onChange={(e) => onRound({ survival_narration_fr: e.target.value })}
              />
            </Field>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  )
}
