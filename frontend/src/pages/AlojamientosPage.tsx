import { useSearchParams } from 'react-router-dom'

import { BuildingsPage } from './BuildingsPage'
import { PropertiesPage } from './PropertiesPage'
import { ReservasPage } from './ReservasPage'

const TABS = [
  { key: 'pisos', label: 'Pisos' },
  { key: 'reservas', label: 'Reservas' },
  { key: 'edificios', label: 'Edificios' },
] as const

export function AlojamientosPage() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some((t) => t.key === params.get('tab')) ? params.get('tab')! : 'pisos'

  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-2 border-b border-line pb-3">
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

      {tab === 'pisos' ? <PropertiesPage /> : null}
      {tab === 'reservas' ? <ReservasPage /> : null}
      {tab === 'edificios' ? <BuildingsPage /> : null}
    </div>
  )
}
