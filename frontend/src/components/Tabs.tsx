import type { ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'

export type TabDef = { key: string; label: string; render: () => ReactNode }

/** Pestañas consistentes en toda la app, sincronizadas con `?tab=` en la URL. */
export function Tabs({ tabs }: { tabs: TabDef[] }) {
  const [params, setParams] = useSearchParams()
  const requested = params.get('tab') ?? ''
  const active = tabs.some((t) => t.key === requested) ? requested : tabs[0].key
  const current = tabs.find((t) => t.key === active) ?? tabs[0]

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2 border-b border-line pb-3">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setParams({ tab: t.key }, { replace: true })}
            className={
              'rounded-full px-4 py-1.5 text-sm font-medium transition ' +
              (active === t.key
                ? 'bg-brand-soft text-brand-ink'
                : 'text-muted hover:bg-sunk hover:text-ink')
            }
          >
            {t.label}
          </button>
        ))}
      </div>
      {current.render()}
    </div>
  )
}
