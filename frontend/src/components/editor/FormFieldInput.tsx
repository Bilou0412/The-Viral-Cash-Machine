// Renders one input bound to a brick param, driven by a FormField descriptor.
// string/number/integer/boolean/enum/file/array → matching control. Values are
// kept as `unknown` and coerced per type on change.

import { useRef, useState } from "react"
import { Link2, Upload, X } from "lucide-react"
import { toast } from "sonner"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  asBrickRef,
  brickRefLabel,
  isConnectableField,
  makeBrickRef,
} from "./brick-helpers"
import type { Brick, FormField } from "@/lib/types"

interface FormFieldInputProps {
  field: FormField
  value: unknown
  onChange: (value: unknown) => void
  /** Other bricks in the doc that can be wired into a connectable field. */
  connectableBricks?: Brick[]
}

const asString = (v: unknown) => (v == null ? "" : String(v))

export function FormFieldInput({
  field,
  value,
  onChange,
  connectableBricks = [],
}: FormFieldInputProps) {
  const id = `field-${field.name}`
  const label = (
    <Label htmlFor={id} className="flex items-center gap-1 text-xs">
      <span className="font-medium">{field.label || field.name}</span>
      {field.required && <span className="text-primary">*</span>}
    </Label>
  )

  // Connection-capable fields get a "free value" ⇄ "connect to a brick" toggle.
  const canConnect =
    isConnectableField(field.name, field.type) && connectableBricks.length > 0
  const connectedTo = asBrickRef(value)

  if (canConnect || connectedTo) {
    return (
      <ConnectableField
        id={id}
        label={label}
        field={field}
        value={value}
        onChange={onChange}
        connectableBricks={connectableBricks}
        connectedTo={connectedTo}
      />
    )
  }

  let control: React.ReactNode

  switch (field.type) {
    case "boolean":
      control = (
        <div className="flex items-center gap-2">
          <Switch id={id} checked={value === true} onCheckedChange={(c) => onChange(c)} />
          <span className="text-xs text-muted-foreground">{value === true ? "oui" : "non"}</span>
        </div>
      )
      break
    case "enum":
      control = (
        <select
          id={id}
          value={asString(value)}
          onChange={(e) => onChange(e.target.value)}
          className="flex h-9 w-full rounded-md border border-input bg-background/60 px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {(field.enum ?? []).map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      )
      break
    case "integer":
    case "number":
      control = (
        <Input
          id={id}
          type="number"
          step={field.type === "integer" ? 1 : "any"}
          value={value === null || value === undefined ? "" : String(value)}
          onChange={(e) => {
            const raw = e.target.value
            if (raw === "") return onChange(null)
            const n = field.type === "integer" ? parseInt(raw, 10) : parseFloat(raw)
            onChange(Number.isNaN(n) ? null : n)
          }}
        />
      )
      break
    case "file":
      control = <FileUpload value={value} onChange={onChange} />
      break
    case "array":
      control = (
        <Textarea
          id={id}
          rows={2}
          placeholder="une valeur par ligne"
          value={Array.isArray(value) ? (value as unknown[]).map(asString).join("\n") : asString(value)}
          onChange={(e) =>
            onChange(e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))
          }
        />
      )
      break
    default: {
      // string — long prompts get a textarea
      const long = /prompt|text|description|narration/i.test(field.name)
      control = long ? (
        <Textarea id={id} rows={3} value={asString(value)} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <Input id={id} type="text" value={asString(value)} onChange={(e) => onChange(e.target.value)} />
      )
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label}
      {control}
      {field.description && (
        <p className="text-[10px] leading-snug text-muted-foreground/70">{field.description}</p>
      )}
    </div>
  )
}

// A field that can either hold a free value or be connected to another brick.
function ConnectableField({
  id,
  label,
  field,
  value,
  onChange,
  connectableBricks,
  connectedTo,
}: {
  id: string
  label: React.ReactNode
  field: FormField
  value: unknown
  onChange: (value: unknown) => void
  connectableBricks: Brick[]
  connectedTo: string | null
}) {
  const sourceBrick = connectedTo
    ? connectableBricks.find((b) => b.id === connectedTo)
    : undefined
  const chipLabel = sourceBrick
    ? brickRefLabel(sourceBrick)
    : connectedTo
      ? `brique ${connectedTo}`
      : ""

  const connectTo = (brickId: string) => {
    if (brickId) onChange(makeBrickRef(brickId))
  }
  const disconnect = () => onChange(field.default ?? null)

  return (
    <div className="flex flex-col gap-1.5">
      {label}
      {connectedTo ? (
        <div className="flex items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-2 py-1.5 text-xs">
          <Link2 className="h-3.5 w-3.5 shrink-0 text-primary" />
          <span className="truncate" title={chipLabel}>
            {chipLabel}
          </span>
          <button
            type="button"
            onClick={disconnect}
            title="Déconnecter (revenir à une valeur libre)"
            className="ml-auto shrink-0 rounded p-0.5 text-muted-foreground hover:text-destructive"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <>
          <Input
            id={id}
            type="text"
            placeholder="URL ou chemin de fichier"
            value={asString(value)}
            onChange={(e) => onChange(e.target.value || null)}
          />
          <select
            aria-label="Connecter à une brique"
            value=""
            onChange={(e) => connectTo(e.target.value)}
            className="flex h-8 w-full rounded-md border border-input bg-background/60 px-2 py-0.5 text-xs text-muted-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="">⛓ Connecter à une brique…</option>
            {connectableBricks.map((b) => (
              <option key={b.id} value={b.id}>
                {brickRefLabel(b)}
              </option>
            ))}
          </select>
        </>
      )}
      {field.description && (
        <p className="text-[10px] leading-snug text-muted-foreground/70">{field.description}</p>
      )}
    </div>
  )
}

/** Upload d'une photo pour un input image (Phase 3). La valeur devient la ref de
 * stockage ; à la génération elle est poussée vers Replicate. Vider = revenir à
 * l'auto-lien (pour l'image de départ d'une vidéo). */
function FileUpload({
  value,
  onChange,
}: {
  value: unknown
  onChange: (value: unknown) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const current = asString(value)

  async function pick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = "" // permet de re-sélectionner le même fichier
    if (!file) return
    setBusy(true)
    try {
      const { ref } = await api.uploadFile(file)
      onChange(ref)
      toast.success("Photo uploadée")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de l'upload")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-1.5">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={pick}
      />
      {current ? (
        <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-2 py-1.5">
          <span className="min-w-0 flex-1 truncate text-xs" title={current}>
            📷 {current.split("/").pop()}
          </span>
          <button
            type="button"
            onClick={() => onChange(null)}
            title="Retirer (revenir à l'auto-lien)"
            className="shrink-0 rounded p-0.5 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="gap-1.5"
        >
          <Upload className="h-3.5 w-3.5" /> {busy ? "Upload…" : "Uploader une photo"}
        </Button>
      )}
    </div>
  )
}
