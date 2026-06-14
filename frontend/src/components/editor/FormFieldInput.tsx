// Renders one input bound to a brick param, driven by a FormField descriptor.
// string/number/integer/boolean/enum/file/array → matching control. Values are
// kept as `unknown` and coerced per type on change.

import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import type { FormField } from "@/lib/types"

interface FormFieldInputProps {
  field: FormField
  value: unknown
  onChange: (value: unknown) => void
}

const asString = (v: unknown) => (v == null ? "" : String(v))

export function FormFieldInput({ field, value, onChange }: FormFieldInputProps) {
  const id = `field-${field.name}`
  const label = (
    <Label htmlFor={id} className="flex items-center gap-1 text-xs">
      <span className="font-medium">{field.name}</span>
      {field.required && <span className="text-primary">*</span>}
    </Label>
  )

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
      control = (
        <Input
          id={id}
          type="text"
          placeholder="URL ou chemin de fichier"
          value={asString(value)}
          onChange={(e) => onChange(e.target.value || null)}
        />
      )
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
