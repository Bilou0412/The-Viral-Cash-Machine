// L'ATELIER — création SCÈNE PAR SCÈNE : l'équipe discute (table ronde) pour
// accoucher d'une scène, la mémoire avance, tu révises, puis scène suivante.

import { useMemo, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"
import { MessagesSquare, PlayCircle, PencilRuler, CheckCircle2, Circle } from "lucide-react"
import { useEditorDocument, useScenesState, useBuildNextScene, useSceneTranscript } from "@/hooks/use-editor"
import { CREW } from "@/lib/crew"
import { isClipBrick } from "@/lib/types"
import type { ClipBrick, Turn } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Spinner, LoadingState } from "@/components/studio/states"

// Couleur de chaque voix à la table ronde (cohérent avec le dossier de prod).
const VOICE_COLOR: Record<string, string> = {
  realisateur: "text-amber-500",
  directeur_artistique: "text-teal-500",
  chef_operateur: "text-sky-500",
  casting: "text-rose-500",
  dialoguiste: "text-violet-500",
}
const roleTitle = (key: string) => CREW.find((r) => r.key === key)?.title ?? key
const asText = (v: unknown) => (typeof v === "string" ? v : "")

export function SceneRoom() {
  const { docId = "" } = useParams()
  const { data: document } = useEditorDocument(docId)
  const state = useScenesState(docId)
  const build = useBuildNextScene(docId)
  const [selected, setSelected] = useState<string | null>(null)

  const arc = state.data?.arc ?? []
  const built = new Set(state.data?.built ?? [])
  const remaining = state.data?.remaining ?? []
  const current = selected ?? state.data?.built.at(-1) ?? null
  const transcript = useSceneTranscript(docId, current && built.has(current) ? current : null)

  const shotsOf = useMemo(() => {
    const scene = (document?.doc.scenes ?? []).find((s) => s.id === current)
    if (!scene) return [] as ClipBrick[]
    const byId = new Map((document?.doc.bricks ?? []).map((b) => [b.id, b]))
    return scene.shot_ids
      .map((id) => byId.get(id))
      .filter((b): b is ClipBrick => !!b && isClipBrick(b))
  }, [document, current])

  const onBuild = () =>
    build.mutate(undefined, {
      onSuccess: (r) => {
        setSelected(r.scene_id)
        toast.success(
          r.source === "fake"
            ? `Scène « ${r.title} » créée (démo) — ${r.transcript.length} échanges`
            : `Scène « ${r.title} » créée 🎬`
        )
      },
      onError: (e) => toast.error(e instanceof Error ? e.message : "La table ronde a échoué"),
    })

  if (state.isLoading) return <LoadingState />

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold">
            <MessagesSquare className="h-5 w-5" /> L'atelier — scène par scène
          </h1>
          <p className="text-sm text-muted-foreground">
            Le réalisateur pose la scène « à trous », chaque métier remplit ses trous, on met en
            commun, puis chacun voit l'ensemble et ajuste (révision). Tu révises, puis on enchaîne —
            la mémoire (bible, continuité) avance.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link to={`/editor/${docId}/review`}>
            <PencilRuler className="h-4 w-4" /> Réviser / éditer les briques
          </Link>
        </Button>
      </div>

      <div className="grid gap-5 md:grid-cols-[220px_1fr]">
        {/* Colonne : l'arc (les scènes) */}
        <div className="space-y-1.5">
          <p className="px-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            L'arc ({built.size}/{arc.length})
          </p>
          {arc.map((s) => {
            const done = built.has(s.id)
            return (
              <button
                key={s.id}
                onClick={() => done && setSelected(s.id)}
                disabled={!done}
                className={`flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  current === s.id ? "border-primary/50 bg-secondary/40" : "border-border"
                } ${done ? "hover:bg-secondary/30" : "opacity-55"}`}
              >
                {done ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                ) : (
                  <Circle className="h-4 w-4 shrink-0 text-muted-foreground/50" />
                )}
                <span className="truncate">{s.title}</span>
              </button>
            )
          })}
          {remaining.length > 0 ? (
            <Button onClick={onBuild} disabled={build.isPending} className="mt-2 w-full gap-2">
              {build.isPending ? <Spinner /> : <PlayCircle className="h-4 w-4" />}
              {built.size === 0 ? "Lancer la 1re scène" : "Scène suivante"}
            </Button>
          ) : (
            <Button asChild className="mt-2 w-full gap-2">
              <Link to={`/editor/${docId}/review`}>
                <CheckCircle2 className="h-4 w-4" /> Toutes les scènes — réviser
              </Link>
            </Button>
          )}
        </div>

        {/* Colonne : la table ronde de la scène courante + son résultat */}
        <div className="space-y-4">
          {build.isPending && (
            <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
              <Spinner /> L'équipe discute…
            </div>
          )}

          {!current && !build.isPending && (
            <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
              Lance la 1re scène : le réalisateur pose le contrat, le DA, le chef op, le casting et le
              dialoguiste remplissent chacun leurs trous, puis révisent en voyant l'ensemble.
            </div>
          )}

          {current && (
            <>
              <section className="rounded-xl border border-border bg-card/40 p-4">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                  <MessagesSquare className="h-4 w-4 text-primary" /> Le contrat, les brouillons & la révision
                </h2>
                {transcript.isLoading ? (
                  <LoadingState />
                ) : (
                  <ol className="space-y-2.5">
                    {(transcript.data?.transcript ?? []).map((t: Turn, i: number) => (
                      <li key={i} className="text-sm">
                        <span className={`font-semibold ${VOICE_COLOR[t.role] ?? "text-foreground"}`}>
                          {roleTitle(t.role)}
                        </span>
                        <span className="text-muted-foreground"> — {t.message}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </section>

              <section className="space-y-2">
                <h2 className="text-sm font-semibold">Ce qu'ils ont produit</h2>
                {shotsOf.map((clip) => (
                  <div key={clip.id} className="rounded-lg border border-border bg-card px-3 py-2 text-sm">
                    <p className="font-mono text-[11px] text-muted-foreground">{clip.id}</p>
                    <p className="text-muted-foreground">{asText(clip.image.params.prompt)}</p>
                    {clip.children.map((ch) => (
                      <p key={ch.id} className="mt-1 text-xs">
                        🎙 « {asText(ch.params.text)} »
                      </p>
                    ))}
                  </div>
                ))}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
