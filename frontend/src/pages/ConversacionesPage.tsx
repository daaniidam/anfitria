import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ConversationsApi, PropertiesApi, ReservationsApi } from '../api/endpoints'
import { Button, Card, EmptyState, Tag } from '../components/ui'
import type { Conversation } from '../types'

const SOURCE_LABEL: Record<string, string> = {
  booking: 'Booking', airbnb: 'Airbnb', direct: 'Directa', other: 'Otro',
}

function fmtDay(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
}

export function ConversacionesPage() {
  const { data: conversations } = useQuery({
    queryKey: ['conversations'],
    queryFn: ConversationsApi.list,
    refetchInterval: 8000,
  })
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const nameOf = (id: number) => properties?.find((p) => p.id === id)?.name ?? 'Piso'

  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selected = conversations?.find((c) => c.id === selectedId) ?? null

  return (
    <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
      <div className="flex flex-col gap-4">
        <header>
          <p className="eyebrow text-brand-ink">Atención</p>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">Conversaciones</h1>
          <p className="mt-1 text-sm text-muted">
            Abre una conversación y toma el control para responder en vivo. La IA se aparta.
          </p>
        </header>
        <div className="flex flex-col gap-1.5">
          {conversations && conversations.length > 0 ? (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedId(c.id)}
                className={
                  'flex items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm transition ' +
                  (c.id === selectedId
                    ? 'border-brand bg-brand-soft text-brand-ink'
                    : 'border-line bg-surface text-ink hover:bg-sunk')
                }
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">{nameOf(c.property_id)}</span>
                  <span className="block truncate text-xs text-muted">{c.guest_ref}</span>
                </span>
                {c.handoff ? <Tag tone="brass">en vivo</Tag> : null}
              </button>
            ))
          ) : (
            <p className="text-sm text-muted">
              Aún no hay conversaciones. Prueba el simulador de huésped.
            </p>
          )}
        </div>
      </div>

      <div>
        {selected ? (
          <Thread conversation={selected} propertyName={nameOf(selected.property_id)} />
        ) : (
          <EmptyState title="Elige una conversación">
            Verás el hilo completo y podrás tomar el control para atender en vivo.
          </EmptyState>
        )}
      </div>
    </div>
  )
}

function Thread({ conversation, propertyName }: { conversation: Conversation; propertyName: string }) {
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

      <Card className="flex max-h-[52vh] flex-col gap-2 overflow-y-auto p-4">
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

      <form onSubmit={onSend} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={conversation.handoff ? 'Escribe al huésped…' : 'Toma el control para escribir en vivo'}
          className="flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        />
        <Button variant="brand" type="submit" disabled={reply.isPending || text.trim().length === 0}>
          {reply.isPending ? 'Enviando…' : 'Enviar'}
        </Button>
      </form>
    </div>
  )
}
