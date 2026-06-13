// Typed API client for the VCM Studio backend (U1 FastAPI). Verified against the
// live contract. All calls go through `/api` (proxied by Vite to :8000).
//
// VITE_USE_MOCKS=true runs the UI against the in-memory mock backend (mocks.ts)
// for offline demos. Default is the real API.

import type {
  AdventureScript,
  Asset,
  BeatsResponse,
  CostEstimate,
  CreateEpisodeBody,
  Episode,
  GenerateScriptBody,
  LibraryItem,
  Project,
} from "./types"
import { mockApi } from "./mocks"

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true"
const BASE = "/api"

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = "ApiError"
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? body.message ?? detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// URL helpers for media that <img>/<video>/<audio> fetch directly.
export const assetFileUrl = (assetId: number) => `${BASE}/assets/${assetId}/file`
export const episodeVideoUrl = (episodeId: number) => `${BASE}/episodes/${episodeId}/video`
export const eventsUrl = (episodeId: number) => `${BASE}/events/${episodeId}`

// ── Real API surface ───────────────────────────────────────────────────

const realApi = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) }),

  listEpisodes: (projectId?: number) =>
    request<Episode[]>(
      projectId == null ? "/episodes" : `/episodes?project_id=${projectId}`
    ),
  getEpisode: (id: number) => request<Episode>(`/episodes/${id}`),
  createEpisode: (body: CreateEpisodeBody) =>
    request<Episode>("/episodes", { method: "POST", body: JSON.stringify(body) }),

  // POST generates (and stores) the AdventureScript from a prompt + character names.
  generateScript: (episodeId: number, body: GenerateScriptBody) =>
    request<AdventureScript>(`/episodes/${episodeId}/script`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getScript: (episodeId: number) =>
    request<AdventureScript>(`/episodes/${episodeId}/script`),
  // PUT expects the script serialized as a JSON string under `script_json`.
  saveScript: (episodeId: number, script: AdventureScript) =>
    request<AdventureScript>(`/episodes/${episodeId}/script`, {
      method: "PUT",
      body: JSON.stringify({ script_json: JSON.stringify(script) }),
    }),

  getBeats: (episodeId: number) => request<BeatsResponse>(`/episodes/${episodeId}/beats`),
  getAssets: (episodeId: number) => request<Asset[]>(`/episodes/${episodeId}/assets`),
  generateAssets: (episodeId: number) =>
    request<{ episode_id: number; status: string }>(
      `/episodes/${episodeId}/assets/generate`,
      { method: "POST" }
    ),
  regenerateAsset: (assetId: number) =>
    request<{ asset_id: number; status: string }>(`/assets/${assetId}/regenerate`, {
      method: "POST",
    }),

  getCost: (episodeId: number) => request<CostEstimate>(`/episodes/${episodeId}/cost`),
  montage: (episodeId: number) =>
    request<{ episode_id: number; final_path: string }>(
      `/episodes/${episodeId}/montage`,
      { method: "POST" }
    ),

  getLibrary: () => request<LibraryItem[]>("/library"),
}

export type StudioApi = typeof realApi

export const api: StudioApi = USE_MOCKS ? (mockApi as StudioApi) : realApi
export const usingMocks = USE_MOCKS
