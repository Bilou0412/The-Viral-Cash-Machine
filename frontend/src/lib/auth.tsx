// Auth (Phase B.1) — hook `useAuth` + garde de route `RequireAuth`.
//
// La source de vérité est GET /api/auth/me (401 = non connecté). En mode mock
// (VITE_USE_MOCKS), `getMe` renvoie un utilisateur canned → toujours authentifié,
// ce qui garde les tests e2e Playwright verts sans backend.

import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { AuthUser } from "@/lib/types"

export function useAuth() {
  const q = useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
    retry: false, // un 401 ne doit pas être retenté
    staleTime: Infinity,
  })
  return {
    user: (q.data ?? null) as AuthUser | null,
    isLoading: q.isLoading,
  }
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Chargement…
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <>{children}</>
}
