import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { InboxApi } from '../api/endpoints'
import { ChatBubble } from '../components/ChatBubble'
import { ConfidenceMeter } from '../components/ConfidenceMeter'
import { Button, Card, EmptyState, Tag, TextArea } from '../components/ui'
import type { InboxItem } from '../types'

export function InboxPage() {
  const { data, isLoading } = useQuery({ queryKey: ['inbox'], queryFn: InboxApi.list })

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="eyebrow text-brand-ink">Supervisión</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Bandeja de aprobación</h1>
        <p className="mt-1 text-sm text-muted">
          Respuestas que la IA ha preparado y esperan tu visto bueno.
        </p>
      </header>

      {isLoading ? (
        <p className="text-sm text-muted">Cargando…</p>
      ) : !data || data.length === 0 ? (
        <EmptyState title="Bandeja al día">
          No hay respuestas pendientes. Cuando un huésped escriba, la IA preparará
          un borrador y aparecerá aquí para que lo revises.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-4">
          {data.map((item) => (
            <ApprovalCard key={item.draft.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}

function ApprovalCard({ item }: { item: InboxItem }) {
  const queryClient = useQueryClient()
  const [text, setText] = useState(item.draft.text)
  const edited = text.trim() !== item.draft.text.trim()

  const approve = useMutation({
    mutationFn: () => InboxApi.approve(item.draft.id, edited ? text : null),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['inbox'] })
      void queryClient.invalidateQueries({ queryKey: ['conv-messages'] })
    },
  })

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-sunk/60 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-display font-semibold text-ink">{item.property_name}</span>
          <Tag tone="muted">{item.guest_ref}</Tag>
          <Tag tone="brand">{item.draft.language.toUpperCase()}</Tag>
        </div>
        <ConfidenceMeter value={item.draft.confidence} />
      </div>

      <div className="flex flex-col gap-3 p-4">
        <ChatBubble direction="in" text={item.inbound_text} tag="Huésped" />

        <div>
          <span className="eyebrow mb-1.5 block text-muted">Borrador de la IA · edítalo si quieres</span>
          <TextArea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted">
            {edited ? 'Editado por ti' : 'Sin cambios'}
          </span>
          <div className="flex gap-2">
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
              {approve.isPending ? 'Enviando…' : edited ? 'Enviar edición' : 'Aprobar y enviar'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  )
}
