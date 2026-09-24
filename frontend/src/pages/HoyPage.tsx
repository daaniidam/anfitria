import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { ConversationsApi, InboxApi, ReservationsApi } from '../api/endpoints'
import { Onboarding } from '../components/Onboarding'
import { TodaySummary } from '../components/TodaySummary'
import { Card, EmptyState, Tag } from '../components/ui'
import type { Conversation, ReservationListItem } from '../types'

const SOURCE_LABEL: Record<string, string> = {
  booking: 'Booking', airbnb: 'Airbnb', direct: 'Directa', other: 'Otro',
}
function todayISO() {
  return new Date().toISOString().slice(0, 10)
}
function longDate() {
  return new Date().toLocaleDateString('es-ES', {
    weekday: 'long', day: 'numeric', month: 'long',
  })
}

export function HoyPage() {
  const navigate = useNavigate()
  const { data: reservations } = useQuery({ queryKey: ['reservations'], queryFn: ReservationsApi.list })
  const { data: inbox } = useQuery({ queryKey: ['inbox'], queryFn: InboxApi.list })
  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: ConversationsApi.list,
    refetchInterval: 10000,
  })

  const today = todayISO()

  // Estado de la conversación de una reserva (por piso + teléfono).
  const convByKey = useMemo(() => {
    const m = new Map<string, Conversation>()
    for (const c of conversations ?? []) m.set(`${c.property_id}|${c.guest_ref}`, c)
    return m
  }, [conversations])
  const pendingConvIds = useMemo(
    () => new Set((inbox ?? []).map((i) => i.conversation_id)),
    [inbox],
  )

  function stayStatus(res: ReservationListItem): { label: string; tone: 'brass' | 'brand' | 'muted' } | null {
    if (!res.guest_ref) return null
    const c = convByKey.get(`${res.property_id}|${res.guest_ref}`)
    if (!c) return null
    if (pendingConvIds.has(c.id)) return { label: 'pendiente', tone: 'brass' }
    if (c.handoff) return { label: 'en vivo', tone: 'brass' }
    return { label: 'en curso', tone: 'brand' }
  }

  const active = (reservations ?? []).filter((r) => r.status !== 'cancelled')
  const arrivals = active.filter((r) => r.check_in === today)
  const departures = active.filter((r) => r.check_out === today)
  const live = (conversations ?? []).filter((c) => c.handoff)

  const goToConv = (id: number) => navigate(`/conversaciones?c=${id}`)

  return (
    <div className="flex flex-col gap-5">
      <Onboarding />
      <header>
        <p className="eyebrow text-brand-ink">Panel</p>
        <h1 className="mt-1 font-display text-2xl font-bold capitalize text-ink">Hoy · {longDate()}</h1>
      </header>

      <TodaySummary />

      <div className="grid gap-5 lg:grid-cols-2">
        <Panel title="Cola de pendientes" hint="Lo que la IA te consulta">
          {inbox && inbox.length > 0 ? (
            inbox.map((it) => (
              <Row key={it.draft.id} onClick={() => goToConv(it.conversation_id)}>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink">{it.inbound_text}</p>
                  <p className="text-xs text-muted">{it.property_name} · {it.guest_ref}</p>
                </div>
                <Tag tone="brass">responder</Tag>
              </Row>
            ))
          ) : (
            <Empty>La IA lo está atendiendo. Nada pendiente. 🎉</Empty>
          )}
        </Panel>

        <Panel title="En vivo" hint="Conversaciones que atiendes tú">
          {live.length > 0 ? (
            live.map((c) => (
              <Row key={c.id} onClick={() => goToConv(c.id)}>
                <p className="truncate text-sm font-medium text-ink">{c.guest_ref}</p>
                <Tag tone="brass">en vivo</Tag>
              </Row>
            ))
          ) : (
            <Empty>Nadie en atención en vivo ahora mismo.</Empty>
          )}
        </Panel>

        <Panel title="Llegadas de hoy" hint="Check-in previsto">
          {arrivals.length > 0 ? (
            arrivals.map((r) => (
              <StayRow key={r.id} res={r} status={stayStatus(r)} />
            ))
          ) : (
            <Empty>Sin llegadas hoy.</Empty>
          )}
        </Panel>

        <Panel title="Salidas de hoy" hint="Check-out previsto">
          {departures.length > 0 ? (
            departures.map((r) => (
              <StayRow key={r.id} res={r} status={stayStatus(r)} />
            ))
          ) : (
            <Empty>Sin salidas hoy.</Empty>
          )}
        </Panel>
      </div>

      {(!reservations || reservations.length === 0) && (!conversations || conversations.length === 0) ? (
        <EmptyState title="Tu día aparecerá aquí">
          Cuando tengas reservas y lleguen mensajes, verás de un vistazo las llegadas, las
          salidas y lo que necesita tu atención.
        </EmptyState>
      ) : null}
    </div>
  )
}

function Panel({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <Card className="p-4">
      <div className="mb-2">
        <span className="eyebrow text-brand-ink">{title}</span>
        <span className="ml-2 text-xs text-muted">{hint}</span>
      </div>
      <div className="flex flex-col gap-1.5">{children}</div>
    </Card>
  )
}

function Row({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface px-3 py-2 text-left transition hover:bg-sunk"
    >
      {children}
    </button>
  )
}

function StayRow({ res, status }: { res: ReservationListItem; status: { label: string; tone: 'brass' | 'brand' | 'muted' } | null }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{res.guest_name}</p>
        <p className="text-xs text-muted">
          {res.property_name} · {SOURCE_LABEL[res.source] ?? res.source}
        </p>
      </div>
      {status ? <Tag tone={status.tone}>{status.label}</Tag> : <span className="text-xs text-muted">sin mensajes</span>}
    </div>
  )
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg bg-sunk/40 px-3 py-4 text-center text-sm text-muted">{children}</p>
}
