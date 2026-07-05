// Hooks React Query pour la bibliothèque de templates (T1).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { CreateTemplateBody } from "@/lib/types"

const qk = {
  all: ["templates"] as const,
  one: (id: string) => ["templates", id] as const,
}

export const useTemplates = () =>
  useQuery({ queryKey: qk.all, queryFn: () => api.listTemplates() })

export const useTemplate = (id: string) =>
  useQuery({ queryKey: qk.one(id), queryFn: () => api.getTemplate(id), enabled: !!id })

export function useCreateTemplate() {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTemplateBody) => api.createTemplate(body),
    onSuccess: () => void c.invalidateQueries({ queryKey: qk.all }),
  })
}

export function useSaveTemplate(id: string) {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateTemplateBody) => api.saveTemplate(id, body),
    onSuccess: (t) => {
      c.setQueryData(qk.one(id), t)
      void c.invalidateQueries({ queryKey: qk.all })
    },
  })
}

export function useDeleteTemplate() {
  const c = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteTemplate(id),
    onSuccess: () => void c.invalidateQueries({ queryKey: qk.all }),
  })
}
