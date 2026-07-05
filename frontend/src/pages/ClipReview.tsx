// R2 — Revue des briques en TIMELINE DE MONTAGE (multipiste).
//
// Comme un logiciel de montage : piste VIDÉO (chaque plan vidéo/photo = une
// brique) et piste SON (la narration/dialogue de chaque plan = une brique alignée
// dessous), sur la même règle de temps. On clique une brique → ses arguments
// (inputs Replicate labellisés métier) s'éditent dans l'inspecteur. Régénération
// ciblée, sauvegarde automatique.

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
const PX_PER_SEC = 64
const RULER_H = 20
const SCENE_H = 22
const LANE_H = 76
const GUTTER = 68
const MIN_BLOCK_PX = 40

type Selection = { clipId: string; childId: string | null }

const promptOf = (n: GenNode | null | undefined): string =>
  n && typeof n.params.prompt === "string" ? n.params.prompt : ""
const textOf = (c: AudioChild): string =>
  typeof c.params.text === "string" ? c.params.text : ""
const short = (s: string, n = 48) => s.replace(/\s+/g, " ").trim().slice(0, n)

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

/** Un bloc de piste (vidéo ou son), positionné par le temps. */
function TrackBlock({
  left,
  width,
  selected,
  onSelect,
  tone,
  thumb,
  icon: Icon,
  badge,
  label,
}: {
  left: number
  width: number
  selected: boolean
  onSelect: () => void
  tone: "video" | "audio"
  thumb?: string | null
  icon: typeof ImageIcon
  badge?: string
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      title={label}
      className={cn(
        "absolute top-1.5 flex h-[calc(100%-0.75rem)] flex-col justify-between overflow-hidden rounded-md border px-2 py-1.5 text-left transition",
        tone === "video"
          ? "bg-primary/10 hover:border-primary/60"
          : "bg-emerald-500/10 hover:border-emerald-500/60",
        selected
          ? "border-primary ring-2 ring-primary"
          : tone === "video"
            ? "border-primary/30"
            : "border-emerald-500/30"
      )}
      style={{ left, width }}
    >
      {thumb && (
        <img
          src={thumb}
          alt=""
          className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-30"
        />
      )}
      <div className="relative flex items-center gap-1.5">
        {badge && (
          <span className="flex h-4 min-w-4 items-center justify-center rounded bg-background/80 px-1 text-[10px] font-bold">
            {badge}
          </span>
        )}
        <Icon
          className={cn(
            "h-3.5 w-3.5 shrink-0",
            tone === "video" ? "text-primary" : "text-emerald-500"
          )}
        />
      </div>
      <span className="relative line-clamp-2 text-[11px] font-medium leading-tight">{label}</span>
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
  const [sel, setSel] = useState<Selection | null>(null)
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

  const clips = useMemo(
    () =>
      (draft?.bricks ?? [])
        .filter(isClipBrick)
        .slice()
        .sort((a, b) => a.placement.start - b.placement.start),
    [draft]
  )

  const thumbById = useMemo(() => {
    const m = new Map<string, string>()
    for (const c of renderModel?.clips ?? []) {
      if (!c.src) continue
      const brickId = c.id.split(":")[0] ?? c.id
      if (!m.has(brickId)) m.set(brickId, c.src)
    }
    return m
  }, [renderModel])

  // Bandes de scène (v3) : span temporel de chaque scène, dérivé de ses briques.
  const sceneBands = useMemo(() => {
    const byId = new Map(clips.map((c) => [c.id, c]))
    const bands: { id: string; title: string; start: number; end: number }[] = []
    for (const s of draft?.scenes ?? []) {
      const members = s.shot_ids.map((id) => byId.get(id)).filter((b): b is ClipBrick => !!b)
      if (members.length === 0) continue
      const start = Math.min(...members.map((m) => m.placement.start))
      const end = Math.max(...members.map((m) => m.placement.start + m.placement.duration))
      bands.push({ id: s.id, title: s.title || s.id, start, end })
    }
    return bands
  }, [draft, clips])

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

  const selection: Selection | null =
    (sel && clips.find((c) => c.id === sel.clipId) ? sel : null) ??
    (clips[0] ? { clipId: clips[0].id, childId: null } : null)
  const selClip = selection ? clips.find((c) => c.id === selection.clipId) ?? null : null
  const selIndex = selClip ? clips.findIndex((c) => c.id === selClip.id) : -1
  const selChild =
    selClip && selection?.childId
      ? selClip.children.find((ch) => ch.id === selection.childId) ?? null
      : null

  const totalSec = Math.max(6, ...clips.map((c) => c.placement.start + c.placement.duration))
  const stripWidth = totalSec * PX_PER_SEC + 16

  const setImage = (params: Record<string, unknown>) =>
    selClip && updateClip(selClip.id, (c) => ({ ...c, image: { ...c.image, params } }))
  const setMotion = (params: Record<string, unknown>) =>
    selClip &&
    updateClip(selClip.id, (c) => ({ ...c, motion: { ...(c.motion as GenNode), params } }))
  const setChildParams = (childId: string, params: Record<string, unknown>) =>
    selClip &&
    updateClip(selClip.id, (c) => ({
      ...c,
      children: c.children.map((ch) => (ch.id === childId ? { ...ch, params } : ch)),
    }))

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="flex items-center gap-2 text-xl font-bold">
          <Clapperboard className="h-5 w-5" /> Revue — {document?.title}
        </h1>
        <p className="text-sm text-muted-foreground">
          La timeline de montage : piste vidéo et piste son. Clique une brique pour éditer ses
          arguments, puis régénère-la. Sauvegarde automatique.
        </p>
      </div>

      {clips.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Aucun plan à réviser dans ce document.
        </p>
      ) : (
        <>
          {/* Timeline multipiste */}
          <div className="rounded-xl border border-border bg-card/40 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Timeline
              </span>
              <span className="text-[11px] text-muted-foreground">{totalSec.toFixed(1)}s</span>
            </div>
            <div className="flex">
              {/* Gouttière : libellés de piste */}
              <div className="shrink-0" style={{ width: GUTTER }}>
                <div style={{ height: RULER_H }} />
                {sceneBands.length > 0 && (
                  <div
                    className="flex items-center text-[10px] font-medium uppercase text-muted-foreground/70"
                    style={{ height: SCENE_H }}
                  >
                    Scènes
                  </div>
                )}
                <div
                  className="flex items-center gap-1 border-t border-border/40 pt-1 text-[10px] font-medium uppercase text-muted-foreground"
                  style={{ height: LANE_H }}
                >
                  <Film className="h-3 w-3" /> Vidéo
                </div>
                <div
                  className="flex items-center gap-1 border-t border-border/40 pt-1 text-[10px] font-medium uppercase text-muted-foreground"
                  style={{ height: LANE_H }}
                >
                  <Mic className="h-3 w-3" /> Son
                </div>
              </div>

              {/* Pistes scrollables */}
              <div className="min-w-0 flex-1 overflow-x-auto pb-2">
                <div className="relative" style={{ width: stripWidth }}>
                  {/* règle temporelle */}
                  <div className="relative" style={{ height: RULER_H }}>
                    {Array.from({ length: Math.ceil(totalSec) + 1 }).map((_, s) => (
                      <div
                        key={s}
                        className="absolute top-0 h-full border-l border-border/40 text-[9px] text-muted-foreground"
                        style={{ left: s * PX_PER_SEC }}
                      >
                        <span className="pl-1">{s}s</span>
                      </div>
                    ))}
                  </div>

                  {/* bandes de SCÈNE */}
                  {sceneBands.length > 0 && (
                    <div className="relative" style={{ height: SCENE_H }}>
                      {sceneBands.map((b) => (
                        <div
                          key={b.id}
                          title={b.title}
                          className="absolute top-0 flex h-[calc(100%-3px)] items-center overflow-hidden rounded-sm border border-primary/40 bg-primary/10 px-1.5 text-[10px] font-medium text-primary"
                          style={{ left: b.start * PX_PER_SEC, width: Math.max(24, (b.end - b.start) * PX_PER_SEC - 3) }}
                        >
                          <span className="truncate">{b.title}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* piste VIDÉO */}
                  <div className="relative border-t border-border/40" style={{ height: LANE_H }}>
                    {clips.map((clip, i) => (
                      <TrackBlock
                        key={clip.id}
                        tone="video"
                        left={clip.placement.start * PX_PER_SEC}
                        width={Math.max(MIN_BLOCK_PX, clip.placement.duration * PX_PER_SEC - 4)}
                        selected={selClip?.id === clip.id && !selChild}
                        onSelect={() => setSel({ clipId: clip.id, childId: null })}
                        thumb={thumbById.get(clip.id) ?? null}
                        icon={clip.kind === "video" ? Film : ImageIcon}
                        badge={String(i + 1)}
                        label={short(promptOf(clip.image) || promptOf(clip.motion)) || `Plan ${i + 1}`}
                      />
                    ))}
                  </div>

                  {/* piste SON */}
                  <div className="relative border-t border-border/40" style={{ height: LANE_H }}>
                    {clips.flatMap((clip) => {
                      const n = clip.children.length || 0
                      return clip.children.map((child, k) => {
                        const w = clip.placement.duration / Math.max(1, n)
                        return (
                          <TrackBlock
                            key={child.id}
                            tone="audio"
                            left={(clip.placement.start + k * w) * PX_PER_SEC}
                            width={Math.max(MIN_BLOCK_PX, w * PX_PER_SEC - 4)}
                            selected={selChild?.id === child.id}
                            onSelect={() => setSel({ clipId: clip.id, childId: child.id })}
                            icon={Mic}
                            label={short(textOf(child)) || child.role}
                          />
                        )
                      })
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Inspecteur de la brique sélectionnée */}
          {selClip && (
            <div className="rounded-xl border border-border bg-card/40 p-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold">
                    {selChild
                      ? `Voix · ${selChild.role}`
                      : `Plan ${selIndex + 1} · ${selClip.kind === "video" ? "Vidéo" : "Photo"}`}
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Plan {selIndex + 1} · {selClip.placement.start.toFixed(1)}s –{" "}
                    {(selClip.placement.start + selClip.placement.duration).toFixed(1)}s
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRegenerate(selClip.id)}
                  disabled={regenerate.isPending}
                  className="gap-1.5"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Régénérer ce plan
                </Button>
              </div>

              {selChild ? (
                <Section icon={Mic} title={`Voix · ${selChild.role}`}>
                  <NodeForm
                    modelRef={selChild.model_ref}
                    kind="voice"
                    params={selChild.params}
                    onChange={(p) => setChildParams(selChild.id, p)}
                  />
                </Section>
              ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                  <Section icon={ImageIcon} title="Image">
                    <NodeForm
                      modelRef={selClip.image.model_ref}
                      kind="image"
                      params={selClip.image.params}
                      onChange={setImage}
                    />
                  </Section>
                  {selClip.kind === "video" && selClip.motion && (
                    <Section icon={Film} title="Vidéo">
                      <NodeForm
                        modelRef={selClip.motion.model_ref}
                        kind="video"
                        params={selClip.motion.params}
                        onChange={setMotion}
                        note="L'image de départ est auto-liée à la photo de ce plan."
                      />
                    </Section>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
