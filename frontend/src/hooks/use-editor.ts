// React Query hooks for the E5 brick editor. Mirrors use-studio.ts conventions:
// centralized cache keys (qkEditor) and invalidation. The render-model query is
// kept fresh as the doc changes so the preview reflects edits.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type {
  CreateEditorDocumentBody,
  DistributionKit,
  EditorDoc,
  GenerativeKind,
} from "@/lib/types"

export const qkEditor = {
  bricks: ["editor", "bricks"] as const,
  modelForm: (modelRef: string) => ["editor", "model-form", modelRef] as const,
  modelSearch: (kind: GenerativeKind, q: string) =>
    ["editor", "model-search", kind, q] as const,
  documents: (projectId: number) => ["editor", "documents", projectId] as const,
  document: (id: string) => ["editor", "document", id] as const,
  episodeDocument: (episodeId: number) =>
    ["editor", "episode-document", episodeId] as const,
  renderModel: (id: string) => ["editor", "render-model", id] as const,
}

export const useBricks = () =>
  useQuery({ queryKey: qkEditor.bricks, queryFn: api.listBricks, staleTime: Infinity })

// Document de scènes d'un épisode (404 = aucun → pas de retry, on retombe legacy).
export const useEpisodeDocument = (episodeId: number, enabled = true) =>
  useQuery({
    queryKey: qkEditor.episodeDocument(episodeId),
    queryFn: () => api.getEpisodeDocument(episodeId),
    enabled: enabled && Number.isFinite(episodeId),
    retry: false,
  })

// model_ref is "owner/name"; split for the endpoint.
export const useModelForm = (modelRef: string | null, kind?: string) =>
  useQuery({
    queryKey: [...qkEditor.modelForm(modelRef ?? ""), kind ?? ""],
    queryFn: () => {
      const [owner = "", name = ""] = (modelRef ?? "").split("/")
      return api.getModelForm(owner, name, kind)
    },
    enabled: !!modelRef && modelRef.includes("/"),
    staleTime: 5 * 60_000,
  })

export const useModelSearch = (kind: GenerativeKind, q: string, enabled: boolean) =>
  useQuery({
    queryKey: qkEditor.modelSearch(kind, q),
    queryFn: () => api.searchModels(kind, q),
    enabled,
    staleTime: 60_000,
  })

export const useEditorDocuments = (projectId: number) =>
  useQuery({
    queryKey: qkEditor.documents(projectId),
    queryFn: () => api.listEditorDocuments(projectId),
    enabled: projectId > 0,
  })

export const useEditorDocument = (id: string) =>
  useQuery({
    queryKey: qkEditor.document(id),
    queryFn: () => api.getEditorDocument(id),
    enabled: !!id,
  })

export const useRenderModel = (id: string) =>
  useQuery({
    queryKey: qkEditor.renderModel(id),
    queryFn: () => api.getRenderModel(id),
    enabled: !!id,
  })

export function useCreateEditorDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateEditorDocumentBody) => api.createEditorDocument(body),
    onSuccess: (doc) => {
      void qc.invalidateQueries({ queryKey: ["editor", "documents"] })
      qc.setQueryData(qkEditor.document(doc.id), doc)
    },
  })
}

export function useSaveEditorDocument(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (doc: EditorDoc) => api.saveEditorDocument(id, doc),
    onSuccess: (saved) => {
      qc.setQueryData(qkEditor.document(id), saved)
      // The render model is derived from the doc — refresh the preview.
      void qc.invalidateQueries({ queryKey: qkEditor.renderModel(id) })
    },
  })
}

export function useGenerateEditorDocument(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.generateEditorDocument(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qkEditor.document(id) }),
  })
}

export function useRegenerateBrick(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (brickId: string) => api.regenerateBrick(id, brickId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qkEditor.document(id) }),
  })
}

export function useRenderEditorDocument(id: string) {
  return useMutation({ mutationFn: () => api.renderEditorDocument(id) })
}

// Directeur artistique : réécrit l'identité visuelle et renvoie le doc à jour.
// On sème le cache du doc (le draft de la revue se re-hydrate) + on rafraîchit
// le render-model (miniatures). Aucun asset n'est régénéré.
export function useDirectArtDirection(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.directArtDirection(id),
    onSuccess: (saved) => {
      qc.setQueryData(qkEditor.document(id), saved)
      void qc.invalidateQueries({ queryKey: qkEditor.renderModel(id) })
    },
  })
}

// Dialoguiste : réécrit le texte parlé et renvoie le doc à jour (même schéma).
export function useDirectDialogue(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.directDialogue(id),
    onSuccess: (saved) => {
      qc.setQueryData(qkEditor.document(id), saved)
      void qc.invalidateQueries({ queryKey: qkEditor.renderModel(id) })
    },
  })
}

// Distribution : l'attaché de presse / Growth. 404 (pas encore de fiche) = normal.
const qkDistribution = (id: string) => ["editor", "distribution", id] as const

export const useDistribution = (id: string) =>
  useQuery({
    queryKey: qkDistribution(id),
    queryFn: () => api.getDistribution(id),
    enabled: !!id,
    retry: false,
  })

export function useGenerateDistribution(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.generateDistribution(id),
    onSuccess: (kit) => qc.setQueryData(qkDistribution(id), kit),
  })
}

export function useSaveDistribution(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (kit: DistributionKit) => api.saveDistribution(id, kit),
    onSuccess: (saved) => qc.setQueryData(qkDistribution(id), saved),
  })
}
