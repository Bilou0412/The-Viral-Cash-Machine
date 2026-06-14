// Right rail: inspector for the selected brick.
//  - GenerativeBrick: model selector + dynamic form (one input per FormField,
//    bound to brick.params), a local context override section, and Régénérer.
//    Switching model keeps params whose field name still exists, resets the rest
//    to the new form's defaults.
//  - MediaBrick: source path + placement.
//  - TextBrick: text payload + placement.

import { useEffect, useRef } from "react"
import { Sparkles, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useModelForm } from "@/hooks/use-editor"
import { BRICK_COLORS, BRICK_LABELS, isConnectableSource } from "./brick-helpers"
import { ModelSelector } from "./ModelSelector"
import { FormFieldInput } from "./FormFieldInput"
import {
  isGenerativeBrick,
  isMediaBrick,
  isTextBrick,
  type Brick,
  type BrickSpec,
  type GenerativeBrick,
  type GlobalContext,
  type MediaBrick,
  type ModelForm,
  type TextBrick,
} from "@/lib/types"
import { cn } from "@/lib/utils"

interface InspectorProps {
  brick: Brick | null
  /** All bricks in the doc — used to offer connection sources. */
  allBricks: Brick[]
  specs: BrickSpec[] | undefined
  /** Ids of bricks that already have a ready generated asset. */
  generatedIds: Set<string>
  onChange: (next: Brick) => void
  onRemove: (id: string) => void
  onRegenerate: (id: string) => void
  regenerating: boolean
}

// Small "non généré" / « généré » status pill, shared by header.
function StatusBadge({ generated }: { generated: boolean }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 text-[10px] font-medium",
        generated
          ? "border-emerald-500/40 bg-emerald-500/15 text-emerald-300"
          : "border-border bg-muted/40 text-muted-foreground"
      )}
    >
      {generated ? "généré" : "non généré"}
    </span>
  )
}

// Apply form defaults, keeping params that still match a field name.
function reconcileParams(
  prev: Record<string, unknown>,
  form: ModelForm
): Record<string, unknown> {
  const next: Record<string, unknown> = {}
  for (const f of form.fields) {
    next[f.name] = f.name in prev ? prev[f.name] : f.default
  }
  return next
}

function PlacementEditor({
  brick,
  onChange,
}: {
  brick: Brick
  onChange: (next: Brick) => void
}) {
  const p = brick.placement
  const set = (patch: Partial<typeof p>) =>
    onChange({ ...brick, placement: { ...p, ...patch } } as Brick)
  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="flex flex-col gap-1">
        <Label className="text-[10px]">Début (s)</Label>
        <Input type="number" step="0.5" value={p.start}
          onChange={(e) => set({ start: Math.max(0, parseFloat(e.target.value) || 0) })} />
      </div>
      <div className="flex flex-col gap-1">
        <Label className="text-[10px]">Durée (s)</Label>
        <Input type="number" step="0.5" value={p.duration}
          onChange={(e) => set({ duration: Math.max(0.5, parseFloat(e.target.value) || 0.5) })} />
      </div>
      <div className="flex flex-col gap-1">
        <Label className="text-[10px]">Piste</Label>
        <Input type="number" step="1" value={p.track}
          onChange={(e) => set({ track: Math.max(0, parseInt(e.target.value, 10) || 0) })} />
      </div>
    </div>
  )
}

function GenerativeInspector({
  brick,
  allBricks,
  specs,
  generated,
  onChange,
  onRegenerate,
  regenerating,
}: {
  brick: GenerativeBrick
  allBricks: Brick[]
  specs: BrickSpec[] | undefined
  generated: boolean
  onChange: (next: Brick) => void
  onRegenerate: (id: string) => void
  regenerating: boolean
}) {
  const spec = specs?.find((s) => s.kind === brick.type)
  const { data: form, isLoading } = useModelForm(brick.model_ref || null)

  // Valid connection sources = other bricks that produce an output.
  const connectableBricks = allBricks.filter(
    (b) => b.id !== brick.id && isConnectableSource(b)
  )

  // When the form arrives for a NEW model, reconcile params (keep overlapping
  // names, default the rest). Track the model_ref we've reconciled to avoid loops.
  const reconciledFor = useRef<string | null>(null)
  useEffect(() => {
    if (!form) return
    if (reconciledFor.current === brick.model_ref) return
    reconciledFor.current = brick.model_ref
    const reconciled = reconcileParams(brick.params, form)
    // Only push an update if it actually changed something.
    const same =
      Object.keys(reconciled).length === Object.keys(brick.params).length &&
      Object.keys(reconciled).every((k) => reconciled[k] === brick.params[k])
    if (!same) onChange({ ...brick, params: reconciled })
  }, [form, brick, onChange])

  const setModel = (modelRef: string) => {
    reconciledFor.current = null // force re-reconcile when its form loads
    onChange({ ...brick, model_ref: modelRef })
  }

  const setParam = (name: string, value: unknown) =>
    onChange({ ...brick, params: { ...brick.params, [name]: value } })

  const ctx = brick.context_overrides ?? {}
  const setCtx = (patch: Partial<GlobalContext>) =>
    onChange({ ...brick, context_overrides: { ...ctx, ...patch } })

  return (
    <div className="flex flex-col gap-4">
      <ModelSelector
        kind={brick.type}
        preferred={spec?.preferred_models ?? []}
        value={brick.model_ref}
        onChange={setModel}
      />

      <div className="border-t border-border pt-3">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Paramètres
        </div>
        {!brick.model_ref && (
          <p className="text-xs text-muted-foreground">Choisis un modèle.</p>
        )}
        {brick.model_ref && isLoading && (
          <p className="text-xs text-muted-foreground">Chargement du formulaire…</p>
        )}
        <div className="flex flex-col gap-3">
          {form?.fields
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((f) => (
              <FormFieldInput
                key={f.name}
                field={f}
                value={brick.params[f.name] ?? f.default}
                onChange={(v) => setParam(f.name, v)}
                connectableBricks={connectableBricks}
              />
            ))}
        </div>
      </div>

      <div className="border-t border-border pt-3">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Contexte (local)
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <Label className="text-[10px]">Texte</Label>
            <Textarea rows={2} value={ctx.text ?? ""}
              placeholder="surcharge du contexte global"
              onChange={(e) => setCtx({ text: e.target.value })} />
          </div>
          <div className="flex flex-col gap-1">
            <Label className="text-[10px]">Direction artistique</Label>
            <Input value={ctx.art_direction ?? ""}
              placeholder="surcharge locale"
              onChange={(e) => setCtx({ art_direction: e.target.value })} />
          </div>
        </div>
      </div>

      <div className="border-t border-border pt-3">
        <PlacementEditor brick={brick} onChange={onChange} />
      </div>

      <div className="flex flex-col gap-2 border-t border-border pt-3">
        <Button
          variant="default"
          size="sm"
          onClick={() => onRegenerate(brick.id)}
          disabled={regenerating || !brick.model_ref}
        >
          <Sparkles className={cn("h-4 w-4", regenerating && "animate-pulse")} />
          {generated ? "Régénérer cette brique" : "Générer cette brique"}
        </Button>
        <p className="text-[10px] leading-snug text-muted-foreground/70">
          Composer la timeline ne génère rien. Lance « Générer » (toutes les
          briques) ou génère cette brique seule quand tu es prêt.
        </p>
      </div>
    </div>
  )
}

function MediaInspector({
  brick,
  onChange,
}: {
  brick: MediaBrick
  onChange: (next: Brick) => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Label className="text-xs">Chemin source</Label>
        <Input value={brick.source_path ?? ""}
          placeholder="exports/.../clip.mp4"
          onChange={(e) => onChange({ ...brick, source_path: e.target.value || undefined })} />
      </div>
      <div className="flex flex-col gap-1">
        <Label className="text-xs">Référence d'asset</Label>
        <Input value={brick.asset_ref ?? ""}
          placeholder="asset id (optionnel)"
          onChange={(e) => onChange({ ...brick, asset_ref: e.target.value || undefined })} />
      </div>
      <div className="border-t border-border pt-3">
        <PlacementEditor brick={brick} onChange={onChange} />
      </div>
    </div>
  )
}

function TextInspector({
  brick,
  onChange,
}: {
  brick: TextBrick
  onChange: (next: Brick) => void
}) {
  const text = typeof brick.payload.text === "string" ? brick.payload.text : ""
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Label className="text-xs">Texte</Label>
        <Textarea rows={3} value={text}
          onChange={(e) => onChange({ ...brick, payload: { ...brick.payload, text: e.target.value } })} />
      </div>
      <div className="border-t border-border pt-3">
        <PlacementEditor brick={brick} onChange={onChange} />
      </div>
    </div>
  )
}

export function Inspector({
  brick,
  allBricks,
  specs,
  generatedIds,
  onChange,
  onRemove,
  onRegenerate,
  regenerating,
}: InspectorProps) {
  if (!brick) {
    return (
      <aside className="flex w-80 shrink-0 flex-col border-l border-border bg-card/40">
        <div className="px-4 py-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Inspecteur
        </div>
        <div className="px-4 text-xs text-muted-foreground">
          Sélectionne une brique pour la modifier.
        </div>
      </aside>
    )
  }

  const c = BRICK_COLORS[brick.type]
  const generated = generatedIds.has(brick.id)

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l border-border bg-card/40">
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
        <span className="flex items-center gap-2">
          <span className={cn("h-2.5 w-2.5 rounded-full", c.dot)} />
          <span className="text-sm font-semibold">{BRICK_LABELS[brick.type]}</span>
          <StatusBadge generated={generated} />
        </span>
        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive"
          onClick={() => onRemove(brick.id)} title="Supprimer">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {isGenerativeBrick(brick) && (
          <GenerativeInspector
            brick={brick}
            allBricks={allBricks}
            specs={specs}
            generated={generated}
            onChange={onChange}
            onRegenerate={onRegenerate}
            regenerating={regenerating}
          />
        )}
        {isMediaBrick(brick) && <MediaInspector brick={brick} onChange={onChange} />}
        {isTextBrick(brick) && <TextInspector brick={brick} onChange={onChange} />}
      </div>
    </aside>
  )
}
