// /editor/:docId — the brick editor. Layout: top bar, left palette, center
// preview, bottom timeline, right inspector. The EditorDoc is the single source
// of truth; edits mutate a local draft and are debounced-saved via React Query.
// The render model (preview) is derived server-side / mock-side from the saved doc.

import { useCallback, useMemo, useRef, useState } from "react"
import { useParams } from "react-router-dom"
import { toast } from "sonner"
import {
  useBricks,
  useEditorDocument,
  useGenerateEditorDocument,
  useRegenerateBrick,
  useRenderEditorDocument,
  useRenderModel,
  useSaveEditorDocument,
} from "@/hooks/use-editor"
import { useEditorEvents } from "@/hooks/use-editor-events"
import { usingMocks } from "@/lib/api"
import { BrickPalette } from "@/components/editor/BrickPalette"
import { RemotionPreview } from "@/components/editor/RemotionPreview"
import { Timeline } from "@/components/editor/Timeline"
import { Inspector } from "@/components/editor/Inspector"
import { EditorTopBar } from "@/components/editor/EditorTopBar"
import { createBrick, type PaletteItem } from "@/components/editor/brick-helpers"
import type { Brick, EditorDoc } from "@/lib/types"

const SAVE_DEBOUNCE_MS = 600

export function Editor() {
  const { docId = "" } = useParams()
  const { data: document, isLoading, isError } = useEditorDocument(docId)
  const { data: specs } = useBricks()
  const { data: renderModel, isLoading: rmLoading } = useRenderModel(docId)

  const save = useSaveEditorDocument(docId)
  const generate = useGenerateEditorDocument(docId)
  const render = useRenderEditorDocument(docId)
  const regenerate = useRegenerateBrick(docId)

  const [jobActive, setJobActive] = useState(false)
  const events = useEditorEvents(docId, jobActive, () => setJobActive(false))

  // Local draft of the doc, kept in sync when the server doc loads/changes.
  // We adjust state during render (React's recommended "store previous prop in
  // state" pattern) keyed on the serialized server doc, rather than an effect.
  const [draft, setDraft] = useState<EditorDoc | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hydratedKey, setHydratedKey] = useState<string | null>(null)
  const serverDocKey = document ? JSON.stringify(document.doc) : null
  if (serverDocKey && hydratedKey !== serverDocKey && document) {
    setHydratedKey(serverDocKey)
    setDraft(document.doc)
  }

  // Debounced save whenever the draft changes (skip the initial hydrate).
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSaved = useRef<string | null>(null)
  const scheduleSave = useCallback(
    (next: EditorDoc) => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => {
        const serialized = JSON.stringify(next)
        if (serialized === lastSaved.current) return
        lastSaved.current = serialized
        save.mutate(next)
      }, SAVE_DEBOUNCE_MS)
    },
    [save]
  )

  const update = useCallback(
    (next: EditorDoc) => {
      setDraft(next)
      scheduleSave(next)
    },
    [scheduleSave]
  )

  const patchDoc = useCallback(
    (patch: Partial<EditorDoc>) => {
      if (!draft) return
      update({ ...draft, ...patch })
    },
    [draft, update]
  )

  const upsertBrick = useCallback(
    (next: Brick) => {
      if (!draft) return
      update({ ...draft, bricks: draft.bricks.map((b) => (b.id === next.id ? next : b)) })
    },
    [draft, update]
  )

  const addBrick = useCallback(
    (item: PaletteItem, track?: number, start?: number) => {
      if (!draft) return
      const brick = createBrick(item, draft.bricks)
      if (track !== undefined) brick.placement.track = track
      if (start !== undefined) brick.placement.start = start
      update({ ...draft, bricks: [...draft.bricks, brick] })
      setSelectedId(brick.id)
    },
    [draft, update]
  )

  const moveBrick = useCallback(
    (id: string, startSec: number, track: number) => {
      if (!draft) return
      update({
        ...draft,
        bricks: draft.bricks.map((b) =>
          b.id === id ? ({ ...b, placement: { ...b.placement, start: startSec, track } } as Brick) : b
        ),
      })
    },
    [draft, update]
  )

  const removeBrick = useCallback(
    (id: string) => {
      if (!draft) return
      update({ ...draft, bricks: draft.bricks.filter((b) => b.id !== id) })
      setSelectedId((cur) => (cur === id ? null : cur))
    },
    [draft, update]
  )

  const selected = useMemo(
    () => draft?.bricks.find((b) => b.id === selectedId) ?? null,
    [draft, selectedId]
  )

  // A brick is "généré" when the derived render model has a clip for it with a
  // non-null src (a ready asset). Audio/voice may legitimately have a null src,
  // so this is a best-effort signal (see report caveat for mock mode).
  const generatedIds = useMemo(() => {
    const ids = new Set<string>()
    for (const clip of renderModel?.clips ?? []) {
      if (clip.src != null) ids.add(clip.id)
    }
    return ids
  }, [renderModel])

  const onGenerate = () => {
    generate.mutate(undefined, {
      onSuccess: () => {
        setJobActive(true)
        toast.success("Génération lancée")
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "Échec de la génération"),
    })
  }

  const onRender = () => {
    render.mutate(undefined, {
      onSuccess: () => {
        setJobActive(true)
        toast.success("Rendu lancé")
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "Échec du rendu"),
    })
  }

  const onRegenerate = (brickId: string) => {
    regenerate.mutate(brickId, {
      onSuccess: () => {
        setJobActive(true)
        toast.success("Régénération de la brique lancée")
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "Échec de la régénération"),
    })
  }

  const progressLabel =
    events.active && events.total > 0
      ? `Génération ${events.done}/${events.total}`
      : null

  if (isError) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 p-8 text-center">
        <p className="text-sm text-destructive">Document éditeur introuvable.</p>
        <a href="/editor" className="text-sm text-primary underline">
          ← Retour aux documents éditeur
        </a>
      </div>
    )
  }
  if (isLoading || !draft) {
    return <div className="p-8 text-sm text-muted-foreground">Chargement de l'éditeur…</div>
  }

  return (
    <div className="flex h-[calc(100vh-0px)] flex-col">
      <EditorTopBar
        doc={draft}
        onPatchDoc={patchDoc}
        onGenerate={onGenerate}
        onRender={onRender}
        generating={generate.isPending}
        rendering={render.isPending}
        saving={save.isPending}
        progressLabel={progressLabel}
      />

      <div className="flex min-h-0 flex-1">
        <BrickPalette onAdd={(item) => addBrick(item)} />

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex min-h-0 flex-1 items-center justify-center bg-background/40 p-4">
            <div className="h-full max-h-full py-2">
              <RemotionPreview model={renderModel} isLoading={rmLoading} />
            </div>
          </div>
          <div className="h-56 shrink-0 border-t border-border bg-card/30">
            <Timeline
              doc={draft}
              selectedId={selectedId}
              generatedIds={generatedIds}
              onSelect={setSelectedId}
              onMoveBrick={moveBrick}
              onDropPalette={(item, track, start) => addBrick(item, track, start)}
            />
          </div>
        </div>

        <Inspector
          brick={selected}
          allBricks={draft.bricks}
          specs={specs}
          generatedIds={generatedIds}
          onChange={upsertBrick}
          onRemove={removeBrick}
          onRegenerate={onRegenerate}
          regenerating={regenerate.isPending}
        />
      </div>

      {usingMocks && (
        <div className="pointer-events-none fixed bottom-2 left-1/2 -translate-x-1/2 rounded-full border border-border bg-card/80 px-3 py-1 text-[10px] text-muted-foreground">
          mode démo (mocks) — SSE désactivé
        </div>
      )}
    </div>
  )
}
