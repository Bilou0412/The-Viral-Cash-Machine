import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Clapperboard } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function Login() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await api.login(email, password)
      await qc.invalidateQueries({ queryKey: ["me"] })
      navigate("/", { replace: true })
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Échec de la connexion")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Clapperboard className="h-5 w-5" />
            </div>
            <CardTitle>VCM Studio</CardTitle>
          </div>
          <CardDescription>Connecte-toi pour accéder au studio.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Connexion…" : "Se connecter"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Pas de compte ?{" "}
            <Link to="/register" className="font-medium text-primary hover:underline">
              Créer un compte
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
