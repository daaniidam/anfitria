import { useState, type FormEvent } from 'react'

import { ApiError } from '../api/client'
import { useAuth } from '../auth'
import { Button, Card, Field } from '../components/ui'

export function LoginPage() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, name, password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'No se pudo continuar')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-ground md:grid-cols-2">
      <section className="hidden flex-col justify-between bg-brand p-10 text-white md:flex">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/15 text-base font-bold">
            A
          </span>
          <span className="font-display text-xl font-bold">AnfitrIA</span>
        </div>
        <div className="max-w-md">
          <p className="eyebrow text-brand-soft">Conserje con IA supervisada</p>
          <h1 className="mt-3 font-display text-4xl leading-[1.05] font-bold text-balance">
            Tu piso responde a los huéspedes. Tú tienes la última palabra.
          </h1>
          <p className="mt-4 text-white/80">
            La IA redacta la respuesta con la información de cada piso; tú la
            apruebas, la editas o dejas que se envíe sola cuando está segura.
          </p>
        </div>
        <p className="font-mono text-xs text-white/60">Check-in · Wifi · Cómo llegar · Normas</p>
      </section>

      <section className="grid place-items-center p-6">
        <Card className="w-full max-w-sm p-6">
          <p className="eyebrow text-brand-ink">{mode === 'login' ? 'Acceso' : 'Crear cuenta'}</p>
          <h2 className="mt-1 mb-5 font-display text-2xl font-bold text-ink">
            {mode === 'login' ? 'Entra al escritorio' : 'Empieza en un minuto'}
          </h2>

          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            {mode === 'register' ? (
              <Field
                label="Nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
              />
            ) : null}
            <Field
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <Field
              label="Contraseña"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />

            {error ? (
              <p className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn">{error}</p>
            ) : null}

            <Button variant="brass" type="submit" disabled={busy} className="mt-1">
              {busy ? 'Un momento…' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
            </Button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError(null)
            }}
            className="mt-4 w-full text-center text-sm text-muted hover:text-ink"
          >
            {mode === 'login'
              ? '¿No tienes cuenta? Crea una'
              : '¿Ya tienes cuenta? Entra'}
          </button>
        </Card>
      </section>
    </div>
  )
}
