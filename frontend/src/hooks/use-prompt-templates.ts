// Hooks React Query pour la bibliothèque de templates de prompt système (T2.1).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { CreatePromptTemplateBody } from "@/lib/types"

const qk = {
  all: ["prompt-templates"] as const,
  one: (id: string) => ["prompt-templates", id] as const,
}

export const usePromptTemplates = () =>
  useQuery({ queryKey: qk.all, queryFn: () => api.listPromptTemplates() })

export const usePromptTemplate = (id: string) =>
  useQuery({
    queryKey: qk.one(id),
    queryFn: () => api.getPromptTemplate(id),
    enabled: !!id,
  })

export function useCreatePromptTemplate() {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (body: CreatePromptTemplateBody) => api.createPromptTemplate(body),
    onSuccess: () => void c.invalidateQueries({ queryKey: qk.all }),
  })
}

export function useSavePromptTemplate(id: string) {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (body: CreatePromptTemplateBody) => api.savePromptTemplate(id, body),
    onSuccess: (t) => {
      c.setQueryData(qk.one(id), t)
      void c.invalidateQueries({ queryKey: qk.all })
    },
  })
}

export function useDeletePromptTemplate() {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deletePromptTemplate(id),
    onSuccess: () => void c.invalidateQueries({ queryKey: qk.all }),
  })
}
