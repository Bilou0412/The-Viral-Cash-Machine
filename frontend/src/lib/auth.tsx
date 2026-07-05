// Auth (Phase B.1) — garde de route `RequireAuth`. Le hook `useAuth` (source de
// vérité GET /api/auth/me) vit dans `@/hooks/use-auth` (convention : hooks dans
// src/hooks/ ; ce fichier n'exporte qu'un composant pour le Fast Refresh).

import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "@/hooks/use-auth"

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
