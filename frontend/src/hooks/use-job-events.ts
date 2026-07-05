// Subscribes to the SSE job stream for one episode and tracks live generation
// progress. The server emits {type, asset_id?, beat?, kind?, index?, total?, ...}.
// We derive a per-beat status map and a coarse progress fraction, invalidating
// the assets cache on each asset_ready/asset_failed. No-op on mocks (no SSE).

import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { eventsUrl, usingMocks } from "@/lib/api"
import { qk } from "./use-studio"
import { beatGroup } from "@/lib/beats"
import type { JobEvent } from "@/lib/types"

export interface BeatProgress {
  status: "generating" | "ready" | "failed"
}

export interface JobProgress {
  /** group key (e.g. "action", "choice.0") -> latest status */
  byGroup: Record<string, BeatProgress>
  done: number
  total: number
  active: boolean
}

const EMPTY: JobProgress = { byGroup: {}, done: 0, total: 0, active: false }

export function useJobEvents(episodeId: number, active: boolean): JobProgress {
  const qc = useQueryClient()
  const [progress, setProgress] = useState<JobProgress>(EMPTY)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!active || usingMocks || episodeId <= 0) return
    const es = new EventSource(eventsUrl(episodeId))
    esRef.current = es

    es.onmessage = (e) => {
      let data: JobEvent
      try {
        data = JSON.parse(e.data as string) as JobEvent
      } catch {
        return // heartbeat / non-JSON
      }
      setProgress((prev) => {
        const byGroup = { ...prev.byGroup }
        let done = prev.done
        let total = prev.total
        let isActive = prev.active

        switch (data.type) {
          case "generation_started":
            isActive = true
            total = data.total ?? prev.total
            break
          case "asset_started":
            if (data.beat) byGroup[beatGroup(data.beat)] = { status: "generating" }
            break
          case "asset_ready":
            if (data.beat) byGroup[beatGroup(data.beat)] = { status: "ready" }
            done += 1
            void qc.invalidateQueries({ queryKey: qk.assets(episodeId) })
            break
          case "asset_failed":
            if (data.beat) byGroup[beatGroup(data.beat)] = { status: "failed" }
            done += 1
            void qc.invalidateQueries({ queryKey: qk.assets(episodeId) })
            break
          case "generation_done":
            isActive = false
            void qc.invalidateQueries({ queryKey: qk.assets(episodeId) })
            void qc.invalidateQueries({ queryKey: qk.episode(episodeId) })
            void qc.invalidateQueries({ queryKey: qk.library })
            break
          case "produce_done":
            // Full pipeline (assets + intro + montage) finished: refresh the
            // episode (status/final_path → final-video shows up), the asset list
            // and the library, without a manual reload.
            isActive = false
            void qc.invalidateQueries({ queryKey: qk.assets(episodeId) })
            void qc.invalidateQueries({ queryKey: qk.episode(episodeId) })
            void qc.invalidateQueries({ queryKey: qk.library })
            break
        }
        return { byGroup, done, total, active: isActive }
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
  }, [episodeId, active, qc])

  return progress
}
