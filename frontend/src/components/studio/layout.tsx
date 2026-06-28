import { NavLink, Outlet } from "react-router-dom"
import { LayoutDashboard, Library, Clapperboard, Sparkles, FolderKanban, Film, KeyRound } from "lucide-react"
import { cn } from "@/lib/utils"
import { usingMocks } from "@/lib/api"
import { Badge } from "@/components/ui/badge"

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projets", icon: FolderKanban, end: false },
  { to: "/editor", label: "Éditeur", icon: Film, end: true },
  { to: "/library", label: "Bibliothèque", icon: Library, end: false },
  { to: "/settings", label: "Réglages", icon: KeyRound, end: false },
]

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 px-4 py-6 md:flex">
        <div className="mb-8 flex items-center gap-2 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-lg shadow-primary/30">
            <Clapperboard className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-bold tracking-tight">VCM Studio</p>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">
              Aventure · 9:16
            </p>
          </div>
        </div>

        <nav className="flex flex-col gap-1">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-secondary text-foreground"
                    : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                )
              }
            >
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
        <main className="flex-1 overflow-y-auto px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
