import { useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ConversationsApi, InboxApi, PropertiesApi, ReservationsApi } from '../api/endpoints'
import { ConfidenceMeter } from '../components/ConfidenceMeter'
import { Onboarding } from '../components/Onboarding'
import { Button, Card, EmptyState, Tag, TextArea } from '../components/ui'
import type { Conversation, InboxItem } from '../types'

type Filter = 'pending' | 'live' | 'all'

const SOURCE_LABEL: Record<string, string> = {
  booking: 'Booking', airbnb: 'Airbnb', direct: 'Directa', other: 'Otro',
}
const REASON_LABEL: Record<string, string> = {
  sin_info: 'No encontró información que encaje en la ficha del piso.',
  poca_confianza: 'No estaba segura de la respuesta (confianza baja).',
  manual: 'Este piso está en modo manual: revisas todas las respuestas.',
}
function fmtDay(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
}

export function BandejaPage() {
  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: ConversationsApi.list,
    refetchInterval: 8000,
  })
  const { data: inbox } = useQuery({ queryKey: ['inbox'], queryFn: InboxApi.list })
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const nameOf = (id: number) => properties?.find((p) => p.id === id)?.name ?? 'Piso'

  const pendingByConv = useMemo(() => {
    const map = new Map<number, InboxItem>()
    for (const it of inbox ?? []) map.set(it.conversation_id, it)
    return map
  }, [inbox])

  const [filter, setFilter] = useState<Filter>('pending')
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const counts = useMemo(() => {
    const all = conversations ?? []
    return {
      pending: all.filter((c) => pendingByConv.has(c.id)).length,
      live: all.filter((c) => c.handoff).length,
      all: all.length,
    }
  }, [conversations, pendingByConv])

  const shown = useMemo(() => {
    const all = conversations ?? []
    const list =
      filter === 'pending'
        ? all.filter((c) => pendingByConv.has(c.id))
        : filter === 'live'
          ? all.filter((c) => c.handoff)
          : all
    // Pendientes primero, luego lo demás por id descendente.
    return [...list].sort((a, b) => {
      const pa = pendingByConv.has(a.id) ? 1 : 0
      const pb = pendingByConv.has(b.id) ? 1 : 0
      return pb - pa || b.id - a.id
    })
  }, [conversations, filter, pendingByConv])

  const selected = shown.find((c) => c.id === selectedId) ?? shown[0] ?? null

  const FILTERS: { key: Filter; label: string; count: number }[] = [
    { key: 'pending', label: 'Pendientes', count: counts.pending },
    { key: 'live', label: 'En vivo', count: counts.live },
    { key: 'all', label: 'Todas', count: counts.all },
  ]

  return (
    <div className="flex flex-col gap-5">
      <Onboarding />
      <header>
        <p className="eyebrow text-brand-ink">Supervisión</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Bandeja</h1>
        <p className="mt-1 text-sm text-muted">
          Todas las conversaciones en un sitio. La IA responde sola cuando está segura; aquí
          respondes lo que te consulta y puedes tomar el control en vivo.
        </p>
      </header>

      <div className="flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={
              'rounded-full border px-3.5 py-1.5 text-sm font-medium transition ' +
              (filter === f.key
                ? 'border-brand bg-brand-soft text-brand-ink'
                : 'border-line bg-surface text-muted hover:bg-sunk')
            }
          >
            {f.label}
            <span className="ml-1.5 font-mono text-xs">{f.count}</span>
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        <div className="flex flex-col gap-1.5">
          {shown.length > 0 ? (
            shown.map((c) => {
              const isPending = pendingByConv.has(c.id)
              return (
                <button
                  key={c.id}
                  onClick={() => setSelectedId(c.id)}
                  className={
                    'flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-left text-sm transition ' +
                    (c.id === selected?.id
                      ? 'border-brand bg-brand-soft text-brand-ink'
                      : 'border-line bg-surface text-ink hover:bg-sunk')
                  }
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{nameOf(c.property_id)}</span>
                    <span className="block truncate text-xs text-muted">{c.guest_ref}</span>
                  </span>
                  {isPending ? (
                    <Tag tone="brass">responder</Tag>
                  ) : c.handoff ? (
                    <Tag tone="brass">en vivo</Tag>
                  ) : null}
                </button>
              )
            })
          ) : (
            <p className="rounded-lg border border-dashed border-line bg-sunk/50 px-3 py-6 text-center text-sm text-muted">
              {filter === 'pending'
                ? 'Nada pendiente: la IA lo está atendiendo.'
                : 'No hay conversaciones aquí.'}
            </p>
          )}
        </div>

        <div>
          {selected ? (
            <Detail
              conversation={selected}
              pending={pendingByConv.get(selected.id) ?? null}
              propertyName={nameOf(selected.property_id)}
            />
          ) : (
            <EmptyState title="Elige una conversación">
              Verás el hilo, la respuesta sugerida por la IA cuando escale, y podrás atender en vivo.
            </EmptyState>
          )}
        </div>
      </div>
    </div>
  )
}

function Detail({
  conversation,
  pending,
  propertyName,
}: {
  conversation: Conversation
  pending: InboxItem | null
  propertyName: string
}) {
  const queryClient = useQueryClient()
  const { data: messages } = useQuery({
    queryKey: ['conv-messages', conversation.id],
    queryFn: () => ConversationsApi.messages(conversation.id),
    refetchInterval: 5000,
  })
  const { data: reservations } = useQuery({ queryKey: ['reservations'], queryFn: ReservationsApi.list })
  const reservation = reservations?.find((r) => r.id === conversation.reservation_id) ?? null

  const [text, setText] = useState('')
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['conversations'] })
    void queryClient.invalidateQueries({ queryKey: ['conv-messages', conversation.id] })
  }
  const takeover = useMutation({ mutationFn: () => ConversationsApi.takeover(conversation.id), onSuccess: invalidate })
  const release = useMutation({ mutationFn: () => ConversationsApi.release(conversation.id), onSuccess: invalidate })
  const reply = useMutation({
    mutationFn: (t: string) => ConversationsApi.reply(conversation.id, t),
    onSuccess: () => {
      setText('')
      invalidate()
    },
  })

  function onSend(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) reply.mutate(text.trim())
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="eyebrow text-brand-ink">{propertyName}</p>
          <h2 className="mt-1 font-display text-xl font-bold text-ink">{conversation.guest_ref}</h2>
        </div>
        {conversation.handoff ? (
          <Button variant="ghost" onClick={() => release.mutate()} disabled={release.isPending}>
            Devolver a la IA
          </Button>
        ) : (
          <Button variant="brand" onClick={() => takeover.mutate()} disabled={takeover.isPending}>
            Tomar el control
          </Button>
        )}
      </header>

      {reservation ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-sm">
          <Tag tone="brand">Reserva</Tag>
          <span className="font-medium text-ink">{reservation.guest_name}</span>
          <span className="text-muted">
            {SOURCE_LABEL[reservation.source] ?? reservation.source} · {fmtDay(reservation.check_in)} → {fmtDay(reservation.check_out)}
          </span>
        </div>
      ) : null}

      {conversation.handoff ? (
        <div className="rounded-lg border border-brass/40 bg-brass-soft/60 px-3 py-2 text-sm text-brass-ink">
          Estás atendiendo en vivo. La IA no responderá hasta que devuelvas el control.
        </div>
      ) : null}

      <Card className="flex max-h-[46vh] flex-col gap-2 overflow-y-auto p-4">
        {messages && messages.length > 0 ? (
          messages.map((m) => (
            <div
              key={m.id}
              className={
                'max-w-[80%] rounded-2xl px-3.5 py-2 text-sm ' +
                (m.direction === 'in'
                  ? 'self-start rounded-bl-sm bg-sunk text-ink'
                  : 'self-end rounded-br-sm bg-brand text-white')
              }
            >
              {m.text}
            </div>
          ))
        ) : (
          <p className="text-sm text-muted">Sin mensajes todavía.</p>
        )}
      </Card>

      {pending ? <ApprovalBox item={pending} /> : null}

      <form onSubmit={onSend} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={conversation.handoff ? 'Escribe al huésped…' : 'Responder directamente al huésped'}
          className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        />
        <Button variant="brand" type="submit" disabled={reply.isPending || text.trim().length === 0}>
          {reply.isPending ? 'Enviando…' : 'Enviar'}
        </Button>
      </form>
    </div>
  )
}

/** Respuesta sugerida por la IA para una escalada: editar, aprender y enviar. */
function ApprovalBox({ item }: { item: InboxItem }) {
  const queryClient = useQueryClient()
  const [text, setText] = useState(item.draft.text)
  const [save, setSave] = useState(true)
  const edited = text.trim() !== item.draft.text.trim()

  const approve = useMutation({
    mutationFn: () => InboxApi.approve(item.draft.id, edited ? text : null, save),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['inbox'] })
      void queryClient.invalidateQueries({ queryKey: ['conv-messages', item.conversation_id] })
      void queryClient.invalidateQueries({ queryKey: ['conversations'] })
      void queryClient.invalidateQueries({ queryKey: ['metrics'] })
    },
  })

  return (
    <Card className="border-brass/40 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="eyebrow text-brass-ink">La IA te consulta · respuesta sugerida</span>
        <ConfidenceMeter value={item.draft.confidence} />
      </div>
      {item.draft.reason && REASON_LABEL[item.draft.reason] ? (
        <p className="mb-2 flex items-start gap-1.5 text-xs text-muted">
          <span aria-hidden className="text-brass-ink">ⓘ</span>
          <span>
            <b className="text-ink">Por qué escaló:</b> {REASON_LABEL[item.draft.reason]}
          </span>
        </p>
      ) : null}
      <TextArea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
      <label className="mt-3 flex items-start gap-2.5 rounded-lg bg-sunk/60 px-3 py-2.5">
        <input
          type="checkbox"
          checked={save}
          onChange={(e) => setSave(e.target.checked)}
          className="mt-0.5 h-4 w-4 accent-brand"
        />
        <span className="text-sm text-ink">
          Guardar en la ficha del piso
          <span className="mt-0.5 block text-xs text-muted">
            La IA lo aprende: la próxima vez que pregunten lo mismo, responderá sola.
          </span>
        </span>
      </label>
      <div className="mt-3 flex items-center justify-end gap-2">
        {edited ? (
          <Button variant="ghost" onClick={() => setText(item.draft.text)}>
            Restablecer
          </Button>
        ) : null}
        <Button
          variant="brass"
          disabled={approve.isPending || text.trim().length === 0}
          onClick={() => approve.mutate()}
        >
          {approve.isPending ? 'Enviando…' : 'Responder al huésped'}
        </Button>
      </div>
    </Card>
  )
}
