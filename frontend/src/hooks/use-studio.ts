// React Query hooks wrapping the typed API client. Centralizes cache keys and
// invalidation so screens stay in sync after mutations.

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type {
  AdventureScript,
  CreateEpisodeBody,
  GenerateScriptBody,
  UpdateAssetBody,
} from "@/lib/types"

export const qk = {
  themes: ["themes"] as const,
  projects: ["projects"] as const,
  episodes: (projectId?: number) => ["episodes", projectId ?? "all"] as const,
  episode: (id: number) => ["episode", id] as const,
  script: (id: number) => ["script", id] as const,
  beats: (id: number) => ["beats", id] as const,
  assets: (id: number) => ["assets", id] as const,
  cost: (id: number) => ["cost", id] as const,
  library: ["library"] as const,
}

export const useThemes = () =>
  useQuery({ queryKey: qk.themes, queryFn: api.listThemes, staleTime: Infinity })

export const useProjects = () =>
  useQuery({ queryKey: qk.projects, queryFn: api.listProjects })

export const useEpisodes = (projectId?: number) =>
  useQuery({ queryKey: qk.episodes(projectId), queryFn: () => api.listEpisodes(projectId) })

export const useEpisode = (id: number) =>
  useQuery({ queryKey: qk.episode(id), queryFn: () => api.getEpisode(id), enabled: id > 0 })

export const useScript = (id: number) =>
  useQuery({
    queryKey: qk.script(id),
    queryFn: () => api.getScript(id),
    enabled: id > 0,
    retry: false, // 404 before a script exists is expected
  })

export const useBeats = (id: number) =>
  useQuery({ queryKey: qk.beats(id), queryFn: () => api.getBeats(id), enabled: id > 0 })

export const useAssets = (id: number) =>
  useQuery({ queryKey: qk.assets(id), queryFn: () => api.getAssets(id), enabled: id > 0 })

export const useCost = (id: number) =>
  useQuery({ queryKey: qk.cost(id), queryFn: () => api.getCost(id), enabled: id > 0 })

export const useLibrary = () =>
  useQuery({ queryKey: qk.library, queryFn: api.getLibrary })

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.createProject(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.projects }),
  })
}

export function useCreateEpisode() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateEpisodeBody) => api.createEpisode(body),
    onSuccess: (ep) => {
      qc.invalidateQueries({ queryKey: ["episodes"] })
      qc.setQueryData(qk.episode(ep.id), ep)
    },
  })
}

export function useGenerateScript(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: GenerateScriptBody) => api.generateScript(episodeId, body),
    onSuccess: (script) => {
      qc.setQueryData(qk.script(episodeId), script)
      qc.invalidateQueries({ queryKey: qk.episode(episodeId) })
    },
  })
}

export function useSaveScript(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (script: AdventureScript) => api.saveScript(episodeId, script),
    onSuccess: (script) => qc.setQueryData(qk.script(episodeId), script),
  })
}

export function useGenerateAssets(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.generateAssets(episodeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets(episodeId) })
      qc.invalidateQueries({ queryKey: qk.episode(episodeId) })
    },
  })
}

export function useRegenerateAsset(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (assetId: number) => api.regenerateAsset(assetId),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.assets(episodeId) }),
  })
}

export function useUpdateAsset(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { assetId: number; body: UpdateAssetBody }) =>
      api.updateAsset(args.assetId, args.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.assets(episodeId) }),
  })
}

export function useMontage(episodeId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.montage(episodeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.episode(episodeId) })
      qc.invalidateQueries({ queryKey: qk.library })
    },
  })
}
