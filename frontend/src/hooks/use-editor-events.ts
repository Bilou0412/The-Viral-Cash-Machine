// SSE progress for an editor document job (generate or render). Reuses the same
// /api/events/{id} stream as episodes, but editor ids are strings and we track a
// coarse done/total + per-brick status keyed by asset_id/beat. No-op on mocks.

import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { eventsUrlFor, usingMocks } from "@/lib/api"
import { qkEditor } from "./use-editor"
import type { JobEvent } from "@/lib/types"

export type BrickStatus = "generating" | "ready" | "failed"

export interface EditorJobProgress {
  active: boolean
  done: number
  total: number
  lastBeat: string | null
  finalPath: string | null
  /** Statut de génération par brique (clé = id de brique, dérivé du `beat`). */
  statusByBrick: Record<string, BrickStatus>
}

const EMPTY: EditorJobProgress = {
  active: false, done: 0, total: 0, lastBeat: null, finalPath: null, statusByBrick: {},
}

/** `beat` = `{brickId}.image|{brickId}.motion|{childId}` → id de brique. */
const brickOfBeat = (beat: string | undefined): string | null =>
  beat ? (beat.split(/[.:]/)[0] ?? null) : null

export function useEditorEvents(
  docId: string,
  active: boolean,
  onDone?: () => void
): EditorJobProgress {
  const qc = useQueryClient()
  const [progress, setProgress] = useState<EditorJobProgress>(EMPTY)
  const esRef = useRef<EventSource | null>(null)
  // Keep the latest onDone without resubscribing on every render.
  const onDoneRef = useRef(onDone)
  useEffect(() => {
    onDoneRef.current = onDone
  }, [onDone])

  useEffect(() => {
    if (!active || usingMocks || !docId) return
    const es = new EventSource(eventsUrlFor(docId))
    esRef.current = es

    es.onmessage = (e) => {
      let data: JobEvent
      try {
        data = JSON.parse(e.data as string) as JobEvent
      } catch {
        return // heartbeat
      }
      setProgress((prev) => {
        let { done, total, active: isActive, lastBeat, finalPath } = prev
        const statusByBrick = { ...prev.statusByBrick }
        const markBrick = (status: BrickStatus) => {
          const id = brickOfBeat(data.beat)
          if (id) statusByBrick[id] = status
        }
        switch (data.type) {
          case "generation_started":
            isActive = true
            total = data.total ?? prev.total
            done = 0
            // Nouveau tournage : on repart d'une ardoise propre.
            for (const k of Object.keys(statusByBrick)) delete statusByBrick[k]
            break
          case "asset_started":
            lastBeat = data.beat ?? prev.lastBeat
            markBrick("generating")
            break
          case "asset_ready":
            done += 1
            lastBeat = data.beat ?? prev.lastBeat
            markBrick("ready")
            void qc.invalidateQueries({ queryKey: qkEditor.document(docId) })
            void qc.invalidateQueries({ queryKey: qkEditor.renderModel(docId) })
            break
          case "asset_failed":
            done += 1
            lastBeat = data.beat ?? prev.lastBeat
            markBrick("failed")
            void qc.invalidateQueries({ queryKey: qkEditor.document(docId) })
            break
          case "generation_done":
          case "produce_done":
            isActive = false
            if (data.local_path) finalPath = data.local_path
            void qc.invalidateQueries({ queryKey: qkEditor.document(docId) })
            void qc.invalidateQueries({ queryKey: qkEditor.renderModel(docId) })
            onDoneRef.current?.()
            break
        }
        return { active: isActive, done, total, lastBeat, finalPath, statusByBrick }
      })
    }
    es.onerror = () => {
      es.close()
      esRef.current = null
    }
    return () => {
      es.close()
      esRef.current = null
    }
  }, [docId, active, qc])

  return progress
}
