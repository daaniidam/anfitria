import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ConversationsApi, PropertiesApi } from '../api/endpoints'
import { ChatBubble } from '../components/ChatBubble'
import { Button, Card, EmptyState } from '../components/ui'

export function GuestSimPage() {
  const queryClient = useQueryClient()
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const [propertyId, setPropertyId] = useState<number | ''>('')
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [text, setText] = useState('')

  const guestRef = '+34 600 · demo'

  const messages = useQuery({
    queryKey: ['conv-messages', conversationId],
    queryFn: () => ConversationsApi.messages(conversationId as number),
    enabled: conversationId !== null,
    refetchInterval: 3500,
  })

  const send = useMutation({
    mutationFn: () =>
      ConversationsApi.inbound({
        property_id: Number(propertyId),
        guest_ref: guestRef,
        text,
      }),
    onSuccess: (result) => {
      setConversationId(result.conversation.id)
      setText('')
      void queryClient.invalidateQueries({ queryKey: ['conv-messages', result.conversation.id] })
    },
  })

  function onSend(event: FormEvent) {
    event.preventDefault()
    if (propertyId !== '' && text.trim()) send.mutate()
  }

  if (properties && properties.length === 0) {
    return (
      <EmptyState title="Primero crea un piso">
        Añade un piso y su ficha de conocimiento en{' '}
        <Link to="/pisos" className="font-medium text-brand-ink underline">
          Pisos
        </Link>{' '}
        y vuelve aquí para probar la conversación.
      </EmptyState>
    )
  }

  const thread = messages.data ?? []

  return (
    <div className="mx-auto flex max-w-md flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Vista del huésped</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Simulador de chat</h1>
        <p className="mt-1 text-sm text-muted">
          Escribe como si fueras el huésped. Verás la respuesta al instante si la
          IA está segura, o cuando la apruebes en la Bandeja.
        </p>
      </header>

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-ink">Piso</span>
        <select
          value={propertyId}
          onChange={(e) => {
            setPropertyId(e.target.value === '' ? '' : Number(e.target.value))
            setConversationId(null)
          }}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          <option value="">Elige un piso…</option>
          {properties?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>

      <Card className="flex h-[26rem] flex-col overflow-hidden">
        <div className="flex items-center gap-2 border-b border-line bg-brand px-4 py-2.5 text-white">
          <span className="grid h-7 w-7 place-items-center rounded-full bg-white/20 text-xs font-bold">
            A
          </span>
          <span className="text-sm font-semibold">Conserje del piso</span>
          <span className="ml-auto font-mono text-[0.68rem] text-brand-soft">WhatsApp · demo</span>
        </div>

        <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto bg-mist/40 p-4">
          {thread.length === 0 ? (
            <p className="m-auto max-w-[16rem] text-center text-sm text-muted">
              Envía un mensaje para empezar. Prueba con “¿Cuál es la contraseña del
              wifi?”.
            </p>
          ) : (
            thread.map((m) => (
              <ChatBubble
                key={m.id}
                direction={m.direction}
                text={m.text}
                tag={m.direction === 'out' ? 'Conserje IA' : undefined}
              />
            ))
          )}
        </div>

        <form onSubmit={onSend} className="flex items-center gap-2 border-t border-line p-3">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Escribe como huésped…"
            className="flex-1 rounded-full border border-line bg-surface px-4 py-2 text-sm text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
          />
          <Button variant="brass" type="submit" disabled={send.isPending || propertyId === ''}>
            Enviar
          </Button>
        </form>
      </Card>
    </div>
  )
}
