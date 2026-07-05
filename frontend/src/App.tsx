import { lazy, Suspense } from "react"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "sonner"
import { Layout } from "@/components/studio/layout"
import { LoadingState } from "@/components/studio/states"
import { RequireAuth } from "@/lib/auth"

// Pages chargées à la demande (code-splitting par route) : le bundle initial
// reste léger et l'éditeur/la revue (Remotion, lourds) ne pèsent que sur leur
// propre route. Chaque `element` est enveloppé d'un Suspense global plus bas.
const Dashboard = lazy(() => import("@/pages/Dashboard").then((m) => ({ default: m.Dashboard })))
const NewEpisode = lazy(() => import("@/pages/NewEpisode").then((m) => ({ default: m.NewEpisode })))
const ScriptEditor = lazy(() => import("@/pages/ScriptEditor").then((m) => ({ default: m.ScriptEditor })))
const Assets = lazy(() => import("@/pages/Assets").then((m) => ({ default: m.Assets })))
const Montage = lazy(() => import("@/pages/Montage").then((m) => ({ default: m.Montage })))
const LibraryPage = lazy(() => import("@/pages/LibraryPage").then((m) => ({ default: m.LibraryPage })))
const Projects = lazy(() => import("@/pages/Projects").then((m) => ({ default: m.Projects })))
const ProjectDetail = lazy(() => import("@/pages/ProjectDetail").then((m) => ({ default: m.ProjectDetail })))
const EpisodeRedirect = lazy(() => import("@/pages/EpisodeRedirect").then((m) => ({ default: m.EpisodeRedirect })))
const Editor = lazy(() => import("@/pages/Editor").then((m) => ({ default: m.Editor })))
const EditorIndex = lazy(() => import("@/pages/EditorIndex").then((m) => ({ default: m.EditorIndex })))
const Settings = lazy(() => import("@/pages/Settings").then((m) => ({ default: m.Settings })))
const Login = lazy(() => import("@/pages/Login").then((m) => ({ default: m.Login })))
const Register = lazy(() => import("@/pages/Register").then((m) => ({ default: m.Register })))
const ClipReview = lazy(() => import("@/pages/ClipReview").then((m) => ({ default: m.ClipReview })))
const TemplatesIndex = lazy(() => import("@/pages/TemplatesIndex").then((m) => ({ default: m.TemplatesIndex })))
const TemplateBuilder = lazy(() => import("@/pages/TemplateBuilder").then((m) => ({ default: m.TemplateBuilder })))
const Creer = lazy(() => import("@/pages/Creer").then((m) => ({ default: m.Creer })))
const PromptTemplatesIndex = lazy(() => import("@/pages/PromptTemplatesIndex").then((m) => ({ default: m.PromptTemplatesIndex })))
const PromptTemplateBuilder = lazy(() => import("@/pages/PromptTemplateBuilder").then((m) => ({ default: m.PromptTemplateBuilder })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 } },
})

const router = createBrowserRouter([
  // Pages d'auth — hors garde (elles doivent charger sans session).
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Dashboard /> },
      { path: "creer", element: <Creer /> },
      { path: "new", element: <NewEpisode /> },
      { path: "projects", element: <Projects /> },
      { path: "projects/:id", element: <ProjectDetail /> },
      { path: "library", element: <LibraryPage /> },
      { path: "settings", element: <Settings /> },
      { path: "editor", element: <EditorIndex /> },
      { path: "editor/:docId/review", element: <ClipReview /> },
      { path: "templates", element: <TemplatesIndex /> },
      { path: "templates/:id", element: <TemplateBuilder /> },
      { path: "prompt-templates", element: <PromptTemplatesIndex /> },
      { path: "prompt-templates/:id", element: <PromptTemplateBuilder /> },
      { path: "episodes/:id", element: <EpisodeRedirect /> },
      { path: "episodes/:id/script", element: <ScriptEditor /> },
      { path: "episodes/:id/assets", element: <Assets /> },
      { path: "episodes/:id/montage", element: <Montage /> },
    ],
  },
  // The editor is a full-screen NLE — rendered outside the studio Layout chrome.
  {
    path: "/editor/:docId",
    element: (
      <RequireAuth>
        <Editor />
      </RequireAuth>
    ),
  },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<LoadingState label="Chargement…" />}>
        <RouterProvider router={router} />
      </Suspense>
      <Toaster theme="dark" position="top-right" richColors closeButton />
    </QueryClientProvider>
  )
}
