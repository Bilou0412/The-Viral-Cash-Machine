import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "sonner"
import { Layout } from "@/components/studio/layout"
import { Dashboard } from "@/pages/Dashboard"
import { NewEpisode } from "@/pages/NewEpisode"
import { ScriptEditor } from "@/pages/ScriptEditor"
import { Assets } from "@/pages/Assets"
import { Montage } from "@/pages/Montage"
import { LibraryPage } from "@/pages/LibraryPage"
import { Projects } from "@/pages/Projects"
import { ProjectDetail } from "@/pages/ProjectDetail"
import { EpisodeRedirect } from "@/pages/EpisodeRedirect"
import { Editor } from "@/pages/Editor"
import { EditorIndex } from "@/pages/EditorIndex"
import { Settings } from "@/pages/Settings"
import { Login } from "@/pages/Login"
import { Register } from "@/pages/Register"
import { RequireAuth } from "@/lib/auth"

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
      { path: "new", element: <NewEpisode /> },
      { path: "projects", element: <Projects /> },
      { path: "projects/:id", element: <ProjectDetail /> },
      { path: "library", element: <LibraryPage /> },
      { path: "settings", element: <Settings /> },
      { path: "editor", element: <EditorIndex /> },
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
      <RouterProvider router={router} />
      <Toaster theme="dark" position="top-right" richColors closeButton />
    </QueryClientProvider>
  )
}
