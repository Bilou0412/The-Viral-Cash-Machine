// Hook d'auth (Phase B.1) — source de vérité : GET /api/auth/me (401 = non
// connecté). En mode mock (VITE_USE_MOCKS), `getMe` renvoie un utilisateur canned
// → toujours authentifié, ce qui garde les tests e2e Playwright verts sans backend.

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useAuth() {
  const q = useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
    retry: false, // un 401 ne doit pas être retenté
    staleTime: Infinity,
  })
  return {
    user: (q.data ?? null),
    isLoading: q.isLoading,
  }
}
