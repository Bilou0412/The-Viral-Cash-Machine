// R2 — Revue des briques générées par l'IA, en TIMELINE chronologique.
//
// Le script est devenu une timeline : chaque `ClipBrick` (un plan de la vidéo)
// est un bloc placé dans l'ordre du montage (largeur ∝ durée). On clique un bloc
// pour éditer SES arguments (tous les inputs Replicate, labellisés métier) dans
// l'inspecteur en dessous, puis on régénère ce plan. Sauvegarde automatique.

import { useCallback, useMemo, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import { Clapperboard, Film, Image as ImageIcon, Mic, RefreshCw } from "lucide-react"
import {
  useEditorDocument,
  useRegenerateBrick,
  useRenderModel,
  useSaveEditorDocument,
  useModelForm,
} from "@/hooks/use-editor"
import { FormFieldInput } from "@/components/editor/FormFieldInput"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { AudioChild, ClipBrick, EditorDoc, GenNode } from "@/lib/types"
import { isClipBrick } from "@/lib/types"

const SAVE_DEBOUNCE_MS = 600
const PX_PER_SEC = 60
const MIN_BLOCK_PX = 96

/** Libellé court d'un plan : le prompt image (ou motion), tronqué. */
function clipLabel(clip: ClipBrick, index: number): string {
  const p =
    (typeof clip.image.params.prompt === "string" && clip.image.params.prompt) ||
    (clip.motion && typeof clip.motion.params.prompt === "string" && clip.motion.params.prompt) ||
    ""
  const short = p.replace(/\s+/g, " ").trim().slice(0, 60)
  return short || `Plan ${index + 1}`
}

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
      {isLoading && <p className="text-xs text-muted-foreground">Chargement des champs…</p>}
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

/** Un bloc de la timeline (un plan), positionné par son placement. */
function TimelineBlock({
  clip,
  index,
  left,
  width,
  thumb,
  generated,
  selected,
  onSelect,
}: {
  clip: ClipBrick
  index: number
  left: number
  width: number
  thumb: string | null
  generated: boolean
  selected: boolean
  onSelect: () => void
}) {
  const Icon = clip.kind === "video" ? Film : ImageIcon
  return (
    <button
      type="button"
      onClick={onSelect}
      title={clipLabel(clip, index)}
      className={cn(
        "absolute top-6 flex h-24 flex-col justify-between overflow-hidden rounded-lg border p-2 text-left transition",
        "bg-secondary/40 hover:border-primary/60",
        selected ? "border-primary ring-2 ring-primary" : "border-border"
      )}
      style={{ left, width }}
    >
      {thumb && (
        <img
          src={thumb}
          alt=""
          className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-40"
        />
      )}
      <div className="relative flex items-center gap-1.5">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-background/80 text-[10px] font-bold">
          {index + 1}
        </span>
        <Icon className="h-3.5 w-3.5 shrink-0 text-primary" />
        <span
          className={cn(
            "ml-auto h-2 w-2 shrink-0 rounded-full",
            generated ? "bg-emerald-500" : "border border-current opacity-40"
          )}
          title={generated ? "généré" : "à générer"}
        />
      </div>
      <span className="relative line-clamp-2 text-[11px] font-medium leading-snug">
        {clipLabel(clip, index)}
      </span>
      {clip.children.length > 0 && (
        <span className="relative flex items-center gap-1 text-[10px] text-muted-foreground">
          <Mic className="h-3 w-3" /> {clip.children.length}
        </span>
      )}
    </button>
  )
}

export function ClipReview() {
  const { docId = "" } = useParams()
  const { data: document, isLoading, isError } = useEditorDocument(docId)
  const { data: renderModel } = useRenderModel(docId)
  const save = useSaveEditorDocument(docId)
  const regenerate = useRegenerateBrick(docId)

  const [draft, setDraft] = useState<EditorDoc | null>(null)
  const [hydratedKey, setHydratedKey] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
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
        bricks: draft.bricks.map((b) => (b.id === clipId && isClipBrick(b) ? updater(b) : b)),
      })
    },
    [draft, update]
  )

  // Plans triés chronologiquement (ordre du montage).
  const clips = useMemo(
    () =>
      (draft?.bricks ?? [])
        .filter(isClipBrick)
        .slice()
        .sort((a, b) => a.placement.start - b.placement.start),
    [draft]
  )

  // brique id -> URL d'aperçu (asset généré prêt), best-effort via le render model.
  const thumbById = useMemo(() => {
    const m = new Map<string, string>()
    for (const c of renderModel?.clips ?? []) {
      if (!c.src) continue
      const brickId = c.id.split(":")[0] ?? c.id
      if (!m.has(brickId)) m.set(brickId, c.src)
    }
    return m
  }, [renderModel])

  const onRegenerate = (clipId: string) =>
    regenerate.mutate(clipId, {
      onSuccess: () => toast.success("Régénération lancée"),
      onError: (e) => toast.error(e instanceof Error ? e.message : "Échec de la régénération"),
    })

  if (isError) {
    return <div className="p-8 text-sm text-destructive">Document introuvable.</div>
  }
  if (isLoading || !draft) {
    return <div className="p-8 text-sm text-muted-foreground">Chargement…</div>
  }

  const selected = clips.find((c) => c.id === selectedId) ?? clips[0] ?? null
  const selectedIndex = selected ? clips.findIndex((c) => c.id === selected.id) : -1
  const totalSec = Math.max(6, ...clips.map((c) => c.placement.start + c.placement.duration))
  const stripWidth = totalSec * PX_PER_SEC + 24

  const setImage = (params: Record<string, unknown>) =>
    selected && updateClip(selected.id, (c) => ({ ...c, image: { ...c.image, params } }))
  const setMotion = (params: Record<string, unknown>) =>
    selected &&
    updateClip(selected.id, (c) => ({ ...c, motion: { ...(c.motion as GenNode), params } }))
  const setChild = (childId: string, params: Record<string, unknown>) =>
    selected &&
    updateClip(selected.id, (c) => ({
      ...c,
      children: c.children.map((ch: AudioChild) =>
        ch.id === childId ? { ...ch, params } : ch
      ),
    }))

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Clapperboard className="h-5 w-5" /> Revue — {document?.title}
        </h1>
        <p className="text-sm text-muted-foreground">
          La timeline de ta vidéo. Clique un plan pour régler ses inputs, puis régénère-le.
          La sauvegarde est automatique.
        </p>
      </div>

      {clips.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Aucun plan à réviser dans ce document.
        </p>
      ) : (
        <>
          {/* Timeline chronologique */}
          <div className="rounded-xl border border-border bg-card/40 p-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Timeline
              </span>
              <span className="text-[11px] text-muted-foreground">{totalSec.toFixed(1)}s</span>
            </div>
            <div className="overflow-x-auto pb-2">
              <div className="relative h-32" style={{ width: stripWidth }}>
                {/* règle temporelle */}
                {Array.from({ length: Math.ceil(totalSec) + 1 }).map((_, s) => (
                  <div
                    key={s}
                    className="absolute top-0 h-4 border-l border-border/50 text-[9px] text-muted-foreground"
                    style={{ left: s * PX_PER_SEC }}
                  >
                    <span className="pl-1">{s}s</span>
                  </div>
                ))}
                {clips.map((clip, i) => (
                  <TimelineBlock
                    key={clip.id}
                    clip={clip}
                    index={i}
                    left={clip.placement.start * PX_PER_SEC}
                    width={Math.max(MIN_BLOCK_PX, clip.placement.duration * PX_PER_SEC - 6)}
                    thumb={thumbById.get(clip.id) ?? null}
                    generated={thumbById.has(clip.id)}
                    selected={selected?.id === clip.id}
                    onSelect={() => setSelectedId(clip.id)}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Inspecteur du plan sélectionné */}
          {selected && (
            <div className="rounded-xl border border-border bg-card/40 p-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold">
                    Plan {selectedIndex + 1} · {selected.kind === "video" ? "Vidéo" : "Photo"}
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    {selected.placement.start.toFixed(1)}s –{" "}
                    {(selected.placement.start + selected.placement.duration).toFixed(1)}s
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRegenerate(selected.id)}
                  disabled={regenerate.isPending}
                  className="gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Régénérer ce plan
                </Button>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <Section icon={ImageIcon} title="Image">
                  <NodeForm
                    modelRef={selected.image.model_ref}
                    kind="image"
                    params={selected.image.params}
                    onChange={setImage}
                  />
                </Section>

                {selected.kind === "video" && selected.motion && (
                  <Section icon={Film} title="Vidéo">
                    <NodeForm
                      modelRef={selected.motion.model_ref}
                      kind="video"
                      params={selected.motion.params}
                      onChange={setMotion}
                      note="L'image de départ est auto-liée à la photo de ce plan."
                    />
                  </Section>
                )}

                {selected.children.map((child) => (
                  <Section key={child.id} icon={Mic} title={`Voix · ${child.role}`}>
                    <NodeForm
                      modelRef={child.model_ref}
                      kind="voice"
                      params={child.params}
                      onChange={(p) => setChild(child.id, p)}
                    />
                  </Section>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
