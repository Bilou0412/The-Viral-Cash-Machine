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

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 } },
})

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "new", element: <NewEpisode /> },
      { path: "projects", element: <Projects /> },
      { path: "projects/:id", element: <ProjectDetail /> },
      { path: "library", element: <LibraryPage /> },
      { path: "episodes/:id", element: <EpisodeRedirect /> },
      { path: "episodes/:id/script", element: <ScriptEditor /> },
      { path: "episodes/:id/assets", element: <Assets /> },
      { path: "episodes/:id/montage", element: <Montage /> },
    ],
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
