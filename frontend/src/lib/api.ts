// Typed API client for the VCM Studio backend (U1 FastAPI). Verified against the
// live contract. All calls go through `/api` (proxied by Vite to :8000).
//
// VITE_USE_MOCKS=true runs the UI against the in-memory mock backend (mocks.ts)
// for offline demos. Default is the real API.

import type {
  AdventureScript,
  Asset,
  AuthUser,
  BeatsResponse,
  Brief,
  BriefResult,
  BrickSpec,
  CostEstimate,
  CreateEditorDocumentBody,
  CreateEpisodeBody,
  DistributionKit,
  DistributionResult,
  EditorDoc,
  EditorDocument,
  EditorDocumentSummary,
  Episode,
  GenerateScriptBody,
  GenerativeKind,
  KeysStatus,
  LibraryItem,
  ModelForm,
  ModelSearchResult,
  Project,
  RenderModel,
  SceneDocumentResult,
  Template,
  TemplateSummary,
  CreateTemplateBody,
  PromptTemplate,
  PromptTemplateSummary,
  CreatePromptTemplateBody,
  Theme,
  UpdateAssetBody,
} from "./types"
import { mockApi, MOCK_PLACEHOLDER_IMG } from "./mocks"

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
    // `credentials: include` envoie le cookie de session (auth Phase B.1).
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string; message?: string }
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
// In mock mode there is no backend, so point at an inline placeholder rather
// than a real /api URL (which the dev proxy would 404).
export const assetFileUrl = (assetId: number) =>
  USE_MOCKS ? MOCK_PLACEHOLDER_IMG : `${BASE}/assets/${assetId}/file`
export const episodeVideoUrl = (episodeId: number) =>
  USE_MOCKS ? MOCK_PLACEHOLDER_IMG : `${BASE}/episodes/${episodeId}/video`
export const editorVideoUrl = (docId: string) =>
  USE_MOCKS ? MOCK_PLACEHOLDER_IMG : `${BASE}/editor/documents/${docId}/video`
export const eventsUrl = (episodeId: number) => `${BASE}/events/${episodeId}`
// SSE for an editor document (B.2 : scope=doc → l'ownership est vérifié côté doc,
// pas épisode ; le bus mélange les deux espaces d'ids).
export const eventsUrlFor = (id: string | number) => `${BASE}/events/${id}?scope=doc`

// ── Real API surface ───────────────────────────────────────────────────

const realApi = {
  // ── Auth (Phase B.1) ─────────────────────────────────────────────────
  // GET /me : 401 si non connecté (le front en déduit qu'il faut se logger).
  getMe: () => request<AuthUser>("/auth/me"),
  login: (email: string, password: string) =>
    request<AuthUser>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<AuthUser>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  listThemes: () => request<Theme[]>("/themes"),

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

  // Document de scènes le plus récent d'un épisode (404 si aucun → chemin legacy).
  // Sert à ouvrir une vidéo directement sur sa revue par scènes.
  getEpisodeDocument: (episodeId: number) =>
    request<EditorDocument>(`/episodes/${episodeId}/editor-document`),

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

  // Matérialise le script de l'épisode en document de briques ÉDITABLE (R1→R2)
  // et renvoie le document → on ouvre la page Réviser dessus.
  reviewFromScript: (episodeId: number) =>
    request<EditorDocument>(`/episodes/${episodeId}/editor-document`, {
      method: "POST",
    }),

  // Le producteur propose un brief complet à partir d'une idée (l'humain édite).
  proposeBrief: (body: { idea: string; partial?: Partial<Brief> }) =>
    request<BriefResult>("/brief/propose", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getBrief: (episodeId: number) => request<Brief>(`/episodes/${episodeId}/brief`),
  saveBrief: (episodeId: number, brief: Brief) =>
    request<Brief>(`/episodes/${episodeId}/brief`, {
      method: "PUT",
      body: JSON.stringify(brief),
    }),

  // Créateur de scènes : idée → l'IA découpe en scènes + plans → document éditable.
  createSceneDocument: (
    episodeId: number,
    body: { prompt: string; style_identity?: string; n_scenes?: number; title?: string }
  ) =>
    request<SceneDocumentResult>(`/episodes/${episodeId}/scene-document`, {
      method: "POST",
      body: JSON.stringify(body),
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
  updateAsset: (assetId: number, body: UpdateAssetBody) =>
    request<Asset>(`/assets/${assetId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  getCost: (episodeId: number) => request<CostEstimate>(`/episodes/${episodeId}/cost`),
  montage: (episodeId: number) =>
    request<{ episode_id: number; final_path: string }>(
      `/episodes/${episodeId}/montage`,
      { method: "POST" }
    ),

  // « Un bouton = toute la vidéo » : assets aventure + intro + montage (fond).
  produce: (episodeId: number) =>
    request<{ episode_id: number; status: string }>(
      `/episodes/${episodeId}/produce`,
      { method: "POST" }
    ),

  getLibrary: () => request<LibraryItem[]>("/library"),

  // ── Editor (E5) ──────────────────────────────────────────────────────
  listBricks: () => request<BrickSpec[]>("/bricks"),

  getModelForm: (owner: string, name: string, kind?: string) =>
    request<ModelForm>(
      `/models/${owner}/${name}/form${kind ? `?kind=${encodeURIComponent(kind)}` : ""}`
    ),

  searchModels: (kind: GenerativeKind, q: string) =>
    request<ModelSearchResult[]>(
      `/models/search?kind=${encodeURIComponent(kind)}&q=${encodeURIComponent(q)}`
    ),

  listEditorDocuments: (projectId: number) =>
    request<EditorDocumentSummary[]>(`/editor/documents?project_id=${projectId}`),
  createEditorDocument: (body: CreateEditorDocumentBody) =>
    request<EditorDocument>("/editor/documents", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getEditorDocument: (id: string) =>
    request<EditorDocument>(`/editor/documents/${id}`),
  saveEditorDocument: (id: string, doc: EditorDoc) =>
    request<EditorDocument>(`/editor/documents/${id}`, {
      method: "PUT",
      body: JSON.stringify({ doc }),
    }),
  generateEditorDocument: (id: string) =>
    request<{ id: string; status: string }>(`/editor/documents/${id}/generate`, {
      method: "POST",
    }),
  regenerateBrick: (id: string, brickId: string) =>
    request<{ id: string; brick_id: string; status: string }>(
      `/editor/documents/${id}/bricks/${brickId}/regenerate`,
      { method: "POST" }
    ),
  getRenderModel: (id: string) =>
    request<RenderModel>(`/editor/documents/${id}/render-model`),
  renderEditorDocument: (id: string) =>
    request<{ id: string; status: string }>(`/editor/documents/${id}/render`, {
      method: "POST",
    }),

  // Distribution : l'attaché de presse / Growth (titre, description, hashtags, hook).
  getDistribution: (id: string) =>
    request<DistributionResult>(`/editor/documents/${id}/distribution`),
  generateDistribution: (id: string) =>
    request<DistributionResult>(`/editor/documents/${id}/distribution`, { method: "POST" }),
  saveDistribution: (id: string, kit: DistributionKit) =>
    request<DistributionResult>(`/editor/documents/${id}/distribution`, {
      method: "PUT",
      body: JSON.stringify(kit),
    }),

  // Upload d'une photo (Phase 3) → ref de stockage à mettre en input image.
  // Multipart : on n'utilise pas `request` (qui force Content-Type JSON).
  uploadFile: async (file: File): Promise<{ ref: string }> => {
    const form = new FormData()
    form.append("file", file)
    const res = await fetch(`${BASE}/uploads`, {
      method: "POST",
      credentials: "include",
      body: form,
    })
    if (!res.ok) {
      let detail = res.statusText
      try {
        const body = (await res.json()) as { detail?: string; message?: string }
        detail = body.detail ?? body.message ?? detail
      } catch {
        /* non-JSON */
      }
      throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText)
    }
    return res.json() as Promise<{ ref: string }>
  },

  // ── Templates (T1) — bibliothèque de structures réutilisables ────────
  listTemplates: () => request<TemplateSummary[]>("/templates"),
  createTemplate: (body: CreateTemplateBody) =>
    request<Template>("/templates", { method: "POST", body: JSON.stringify(body) }),
  getTemplate: (id: string) => request<Template>(`/templates/${id}`),
  saveTemplate: (id: string, body: CreateTemplateBody) =>
    request<Template>(`/templates/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteTemplate: (id: string) =>
    request<{ ok: boolean }>(`/templates/${id}`, { method: "DELETE" }),

  // ── Templates de prompt système (T2.1) ──────────────────────────────
  listPromptTemplates: () => request<PromptTemplateSummary[]>("/prompt-templates"),
  createPromptTemplate: (body: CreatePromptTemplateBody) =>
    request<PromptTemplate>("/prompt-templates", { method: "POST", body: JSON.stringify(body) }),
  getPromptTemplate: (id: string) => request<PromptTemplate>(`/prompt-templates/${id}`),
  savePromptTemplate: (id: string, body: CreatePromptTemplateBody) =>
    request<PromptTemplate>(`/prompt-templates/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deletePromptTemplate: (id: string) =>
    request<{ ok: boolean }>(`/prompt-templates/${id}`, { method: "DELETE" }),

  // BYOK API keys (entered in Settings). GET = status only; PUT saves non-empty.
  getKeysStatus: () => request<KeysStatus>("/settings/keys"),
  saveKeys: (body: { openai?: string; replicate?: string }) =>
    request<KeysStatus>("/settings/keys", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
}

export type StudioApi = typeof realApi

export const api: StudioApi = USE_MOCKS ? (mockApi) : realApi
export const usingMocks = USE_MOCKS
