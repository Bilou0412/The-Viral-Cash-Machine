import { NavLink, Outlet, useNavigate, Link } from "react-router-dom"
import { Library, Clapperboard, Sparkles, Wand2, FolderKanban, Film, KeyRound, LogOut, LayoutTemplate } from "lucide-react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { cn } from "@/lib/utils"
import { api, usingMocks } from "@/lib/api"
import { useAuth } from "@/hooks/use-auth"
import { Badge } from "@/components/ui/badge"

// Nav resserrée : l'essentiel du parcours créateur en haut, l'outillage avancé
// (templates/styles/NLE) replié dessous. Le logo ramène au Dashboard.
const primaryNav = [
  { to: "/creer", label: "Créer", icon: Wand2, end: false },
  { to: "/projects", label: "Mes vidéos", icon: FolderKanban, end: false },
  { to: "/library", label: "Bibliothèque", icon: Library, end: false },
  { to: "/settings", label: "Réglages", icon: KeyRound, end: false },
]
const advancedNav = [
  { to: "/templates", label: "Templates", icon: LayoutTemplate, end: false },
  { to: "/prompt-templates", label: "Styles", icon: Sparkles, end: false },
  { to: "/editor", label: "Éditeur", icon: Film, end: true },
]

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
    isActive
      ? "bg-secondary text-foreground"
      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
  )

export function Layout() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { data: keys } = useQuery({ queryKey: ["keys"], queryFn: () => api.getKeysStatus() })
  const keyMissing = keys && (!keys.openai_set || !keys.replicate_set)

  async function logout() {
    try {
      await api.logout()
    } finally {
      await qc.invalidateQueries({ queryKey: ["me"] })
      void navigate("/login", { replace: true })
    }
  }

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 px-4 py-6 md:flex">
        <Link to="/" className="mb-8 flex items-center gap-2 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-lg shadow-primary/30">
            <Clapperboard className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-bold tracking-tight">VCM Studio</p>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Aventure · 9:16
            </p>
          </div>
        </Link>

        <nav className="flex flex-col gap-1">
          {primaryNav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}

          <p className="mt-4 mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
            Avancé
          </p>
          {advancedNav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto space-y-2 px-2">
          {usingMocks && (
            <Badge variant="warning" className="w-full justify-center gap-1">
              <Sparkles className="h-3 w-3" /> Mode démo (mocks)
            </Badge>
          )}
          {user && (
            <div className="flex items-center justify-between gap-2 rounded-md bg-secondary/40 px-2 py-1.5">
              <span className="truncate text-xs text-muted-foreground" title={user.email}>
                {user.email}
              </span>
              <button
                onClick={logout}
                title="Se déconnecter"
                className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <p className="text-[10px] text-muted-foreground/70">
            Studio vidéo IA · TikTok / Shorts / Reels
          </p>
        </div>
      </aside>

      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex items-center gap-2 border-b border-border bg-card/40 px-4 py-3 md:hidden">
          <Clapperboard className="h-5 w-5 text-primary" />
          <span className="font-bold">VCM Studio</span>
        </header>
        {keyMissing && (
          <Link
            to="/settings"
            className="flex items-center gap-2 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-600 transition-colors hover:bg-amber-500/20 dark:text-amber-400 md:px-8"
          >
            <KeyRound className="h-4 w-4 shrink-0" />
            Ajoute tes clés OpenAI et Replicate dans Réglages pour pouvoir générer.
          </Link>
        )}
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
