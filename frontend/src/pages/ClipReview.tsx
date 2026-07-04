// R2 — Revue des briques générées par l'IA. Chaque `ClipBrick` (un asset de la
// vidéo) est dépliée en sous-formulaires COMPLETS par modèle : Image, Vidéo,
// Voix — tous les inputs Replicate, labellisés métier, pré-remplis par le script.
// Le template à remplir. On régénère ciblé, on ne touche que ce qu'on modifie.

import { useCallback, useMemo, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { Clapperboard, Film, Image as ImageIcon, Mic, RefreshCw } from "lucide-react"
import {
  useEditorDocument,
  useRegenerateBrick,
  useSaveEditorDocument,
  useModelForm,
} from "@/hooks/use-editor"
import { FormFieldInput } from "@/components/editor/FormFieldInput"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import type { AudioChild, Brick, ClipBrick, EditorDoc, GenNode } from "@/lib/types"
import { isClipBrick } from "@/lib/types"

const SAVE_DEBOUNCE_MS = 600

/** Formulaire complet d'un nœud génératif (image / motion / voix). */
function NodeForm({
  modelRef,
  kind,
  params,
  onChange,
  note,
}: {
  modelRef: string
  kind: "image" | "video" | "voice"
  params: Record<string, unknown>
  onChange: (next: Record<string, unknown>) => void
  note?: string
}) {
  const { data: form, isLoading } = useModelForm(modelRef || null, kind)
  return (
    <div className="space-y-3">
      {note && (
        <p className="rounded-md bg-secondary/40 px-2 py-1.5 text-xs text-muted-foreground">
          {note}
        </p>
      )}
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground/70">
        Modèle · {modelRef || "—"}
      </p>
      {isLoading && (
        <p className="text-xs text-muted-foreground">Chargement des champs…</p>
      )}
      {form?.fields
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((f) => (
          <FormFieldInput
            key={f.name}
            field={f}
            value={params[f.name] ?? f.default}
            onChange={(v) => onChange({ ...params, [f.name]: v })}
          />
        ))}
    </div>
  )
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof ImageIcon
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-3 rounded-lg border border-border/60 p-3">
      <p className="flex items-center gap-2 text-sm font-semibold">
        <Icon className="h-4 w-4 text-primary" /> {title}
      </p>
      {children}
    </div>
  )
}

export function ClipReview() {
  const { docId = "" } = useParams()
  const { data: document, isLoading, isError } = useEditorDocument(docId)
  const save = useSaveEditorDocument(docId)
  const regenerate = useRegenerateBrick(docId)

  const [draft, setDraft] = useState<EditorDoc | null>(null)
  const [hydratedKey, setHydratedKey] = useState<string | null>(null)
  const serverKey = document ? JSON.stringify(document.doc) : null
  if (serverKey && hydratedKey !== serverKey && document) {
    setHydratedKey(serverKey)
    setDraft(document.doc)
  }

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const update = useCallback(
    (next: EditorDoc) => {
      setDraft(next)
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => save.mutate(next), SAVE_DEBOUNCE_MS)
    },
    [save]
  )

  const updateClip = useCallback(
    (clipId: string, updater: (c: ClipBrick) => ClipBrick) => {
      if (!draft) return
      update({
        ...draft,
        bricks: draft.bricks.map((b) =>
          b.id === clipId && isClipBrick(b) ? updater(b) : b
        ) as Brick[],
      })
    },
    [draft, update]
  )

  const clips = useMemo(
    () => (draft?.bricks ?? []).filter(isClipBrick),
    [draft]
  )

  const onRegenerate = (clipId: string) =>
    regenerate.mutate(clipId, {
      onSuccess: () => toast.success("Régénération lancée"),
      onError: (e) =>
        toast.error(e instanceof Error ? e.message : "Échec de la régénération"),
    })

  if (isError) {
    return (
      <div className="p-8 text-sm text-destructive">Document introuvable.</div>
    )
  }
  if (isLoading || !draft) {
    return <div className="p-8 text-sm text-muted-foreground">Chargement…</div>
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Clapperboard className="h-5 w-5" /> Revue — {document?.title}
        </h1>
        <p className="text-sm text-muted-foreground">
          Le script est devenu un template : règle les inputs de chaque asset, puis
          régénère ce que tu touches. La sauvegarde est automatique.
        </p>
      </div>

      {clips.length === 0 && (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Aucune brique à réviser dans ce document.
        </p>
      )}

      {clips.map((clip, i) => {
        const setImage = (params: Record<string, unknown>) =>
          updateClip(clip.id, (c) => ({ ...c, image: { ...c.image, params } }))
        const setMotion = (params: Record<string, unknown>) =>
          updateClip(clip.id, (c) => ({
            ...c,
            motion: { ...(c.motion as GenNode), params },
          }))
        const setChild = (childId: string, params: Record<string, unknown>) =>
          updateClip(clip.id, (c) => ({
            ...c,
            children: c.children.map((ch: AudioChild) =>
              ch.id === childId ? { ...ch, params } : ch
            ),
          }))

        return (
          <Card key={clip.id}>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">
                Brique {i + 1} · {clip.kind === "video" ? "Vidéo" : "Photo"}
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onRegenerate(clip.id)}
                disabled={regenerate.isPending}
                className="gap-1.5"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Régénérer
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <Section icon={ImageIcon} title="Image">
                <NodeForm
                  modelRef={clip.image.model_ref}
                  kind="image"
                  params={clip.image.params}
                  onChange={setImage}
                />
              </Section>

              {clip.kind === "video" && clip.motion && (
                <Section icon={Film} title="Vidéo">
                  <NodeForm
                    modelRef={clip.motion.model_ref}
                    kind="video"
                    params={clip.motion.params}
                    onChange={setMotion}
                    note="L'image de départ est auto-liée à la photo de cette brique. (Upload d'une photo perso : bientôt.)"
                  />
                </Section>
              )}

              {clip.children.map((child) => (
                <Section key={child.id} icon={Mic} title={`Voix · ${child.role}`}>
                  <NodeForm
                    modelRef={child.model_ref}
                    kind="voice"
                    params={child.params}
                    onChange={(p) => setChild(child.id, p)}
                  />
                </Section>
              ))}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
