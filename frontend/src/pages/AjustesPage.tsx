import { useSearchParams } from 'react-router-dom'

import { AuditPage } from './AuditPage'
import { EquipoPage } from './EquipoPage'
import { GuestSimPage } from './GuestSimPage'
import { IntegracionesPage } from './IntegracionesPage'
import { MetricsPage } from './MetricsPage'

const TABS = [
  { key: 'equipo', label: 'Equipo' },
  { key: 'integraciones', label: 'Integraciones' },
  { key: 'metricas', label: 'Métricas' },
  { key: 'auditoria', label: 'Auditoría' },
  { key: 'simulador', label: 'Simulador (demo)' },
] as const

export function AjustesPage() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some((t) => t.key === params.get('tab')) ? params.get('tab')! : 'equipo'

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2 border-b border-line pb-3">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setParams({ tab: t.key }, { replace: true })}
            className={
              'rounded-full px-4 py-1.5 text-sm font-medium transition ' +
              (tab === t.key
                ? 'bg-brand-soft text-brand-ink'
                : 'text-muted hover:bg-sunk hover:text-ink')
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'equipo' ? <EquipoPage /> : null}
      {tab === 'integraciones' ? <IntegracionesPage /> : null}
      {tab === 'metricas' ? <MetricsPage /> : null}
      {tab === 'auditoria' ? <AuditPage /> : null}
      {tab === 'simulador' ? <GuestSimPage /> : null}
    </div>
  )
}
