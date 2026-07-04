// SSE progress for an editor document job (generate or render). Reuses the same
// /api/events/{id} stream as episodes, but editor ids are strings and we track a
// coarse done/total + per-brick status keyed by asset_id/beat. No-op on mocks.

import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { eventsUrlFor, usingMocks } from "@/lib/api"
import { qkEditor } from "./use-editor"
import type { JobEvent } from "@/lib/types"

export interface EditorJobProgress {
  active: boolean
  done: number
  total: number
  lastBeat: string | null
  finalPath: string | null
}

const EMPTY: EditorJobProgress = {
  active: false, done: 0, total: 0, lastBeat: null, finalPath: null,
}

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
        switch (data.type) {
          case "generation_started":
            isActive = true
            total = data.total ?? prev.total
            done = 0
            break
          case "asset_started":
            lastBeat = data.beat ?? prev.lastBeat
            break
          case "asset_ready":
          case "asset_failed":
            done += 1
            lastBeat = data.beat ?? prev.lastBeat
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
        return { active: isActive, done, total, lastBeat, finalPath }
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
