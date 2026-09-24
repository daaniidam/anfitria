import { useQuery } from '@tanstack/react-query'

import { ConversationsApi, InboxApi, ReservationsApi } from '../api/endpoints'

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

interface Tile {
  label: string
  value: number
  icon: string
  highlight?: boolean
}

/** Resumen de "hoy" para orientar al anfitrión de un vistazo. */
export function TodaySummary() {
  const { data: reservations } = useQuery({ queryKey: ['reservations'], queryFn: ReservationsApi.list })
  const { data: inbox } = useQuery({ queryKey: ['inbox'], queryFn: InboxApi.list })
  const { data: conversations } = useQuery({ queryKey: ['conversations'], queryFn: ConversationsApi.list })

  const today = todayISO()
  const active = (reservations ?? []).filter((r) => r.status !== 'cancelled')
  const arrivals = active.filter((r) => r.check_in === today).length
  const departures = active.filter((r) => r.check_out === today).length
  const pending = inbox?.length ?? 0
  const live = (conversations ?? []).filter((c) => c.handoff).length

  const tiles: Tile[] = [
    { label: 'Llegadas hoy', value: arrivals, icon: '🛬' },
    { label: 'Salidas hoy', value: departures, icon: '🛫' },
    { label: 'Pendientes', value: pending, icon: '📨', highlight: pending > 0 },
    { label: 'En vivo', value: live, icon: '🎧', highlight: live > 0 },
  ]

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <div
          key={t.label}
          className={
            'rounded-xl border px-4 py-3 ' +
            (t.highlight ? 'border-brass/40 bg-brass-soft/50' : 'border-line bg-surface')
          }
        >
          <div className="flex items-center gap-1.5">
            <span aria-hidden className="text-base">{t.icon}</span>
            <span className="eyebrow text-muted">{t.label}</span>
          </div>
          <div
            className={
              'mt-1 font-display text-2xl font-bold tabular-nums ' +
              (t.highlight ? 'text-brass-ink' : 'text-ink')
            }
          >
            {t.value}
          </div>
        </div>
      ))}
    </div>
  )
}
