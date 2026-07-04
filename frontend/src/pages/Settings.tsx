import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { KeyRound } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

function statusBadge(set?: boolean) {
  return set ? (
    <span className="text-xs font-medium text-green-500">✓ configurée</span>
  ) : (
    <span className="text-xs font-medium text-muted-foreground">✗ manquante</span>
  )
}

export function Settings() {
  const qc = useQueryClient()
  const { data: status } = useQuery({
    queryKey: ["keys"],
    queryFn: () => api.getKeysStatus(),
  })
  const [openai, setOpenai] = useState("")
  const [replicate, setReplicate] = useState("")
  const [saving, setSaving] = useState(false)

  async function save() {
    if (!openai && !replicate) {
      toast.error("Renseigne au moins une clé.")
      return
    }
    setSaving(true)
    try {
      await api.saveKeys({
        openai: openai || undefined,
        replicate: replicate || undefined,
      })
      setOpenai("")
      setReplicate("")
      await qc.invalidateQueries({ queryKey: ["keys"] })
      toast.success("Clés enregistrées")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Échec de l'enregistrement")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <KeyRound className="h-5 w-5" /> Réglages — clés API
        </h1>
        <p className="text-sm text-muted-foreground">
          Tes clés personnelles sont <strong>chiffrées côté serveur</strong> et ne
          sont jamais réaffichées. Chaque compte a les siennes ; tu génères à tes
          propres frais.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Clés de génération</CardTitle>
          <CardDescription>
            OpenAI = écriture du script · Replicate = image / vidéo / voix
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="openai" className="flex items-center justify-between">
              <span>OpenAI API key</span>
              {statusBadge(status?.openai_set)}
            </Label>
            <Input
              id="openai"
              type="password"
              placeholder="sk-…"
              value={openai}
              onChange={(e) => setOpenai(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="replicate" className="flex items-center justify-between">
              <span>Replicate API token</span>
              {statusBadge(status?.replicate_set)}
            </Label>
            <Input
              id="replicate"
              type="password"
              placeholder="r8_…"
              value={replicate}
              onChange={(e) => setReplicate(e.target.value)}
            />
          </div>

          <Button onClick={save} disabled={saving}>
            {saving ? "Enregistrement…" : "Enregistrer"}
          </Button>
          <p className="text-xs text-muted-foreground">
            Laisser un champ vide n'efface pas la clé déjà enregistrée.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
