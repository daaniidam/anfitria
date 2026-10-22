import { NavLink } from 'react-router-dom'

import { Card } from '../components/ui'
import { IntegracionesPage } from './IntegracionesPage'
import { WhatsAppSetupPage } from './WhatsAppSetupPage'

/** Puesta en marcha en un sitio: conectar el PMS y WhatsApp, y probar. */
export function ConfiguracionPage() {
  return (
    <div className="flex flex-col gap-8">
      <header>
        <p className="eyebrow text-brand-ink">Puesta en marcha</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Deja tu conserje listo</h1>
        <p className="mt-1 text-sm text-muted">
          Todo lo de conectar, en un sitio: trae tu cartera desde el PMS (opcional) y conecta
          tu WhatsApp. Cada parte se marca sola cuando la terminas.
        </p>
      </header>

      <section>
        <IntegracionesPage />
      </section>

      <div className="border-t border-line" />

      <section>
        <WhatsAppSetupPage />
      </section>

      <Card className="p-4">
        <p className="text-sm text-ink">¿Todo conectado? Compruébalo escribiendo como un huésped.</p>
        <NavLink
          to="/probar"
          className="mt-2 inline-flex rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:bg-brand-ink"
        >
          Abrir el simulador →
        </NavLink>
      </Card>
    </div>
  )
}
