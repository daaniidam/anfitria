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
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Escaladas</h1>
        <p className="mt-1 text-sm text-muted">
          La IA responde sola cuando está segura. Aquí solo caen los casos que
          prefirió consultarte — el huésped ya recibió un mensaje de espera.
        </p>
      </header>

      {isLoading ? (
        <p className="text-sm text-muted">Cargando…</p>
      ) : !data || data.length === 0 ? (
        <EmptyState title="Sin escaladas">
          La IA está atendiendo a los huéspedes por su cuenta. Cuando dude sobre
          algo, aparecerá aquí para que respondas tú.
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
  const [save, setSave] = useState(true)
  const edited = text.trim() !== item.draft.text.trim()

  const approve = useMutation({
    mutationFn: () => InboxApi.approve(item.draft.id, edited ? text : null, save),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['inbox'] })
      void queryClient.invalidateQueries({ queryKey: ['conv-messages'] })
      void queryClient.invalidateQueries({ queryKey: ['metrics'] })
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
          <span className="eyebrow mb-1.5 block text-muted">
            Respuesta sugerida por la IA · edítala si quieres
          </span>
          <TextArea rows={3} value={text} onChange={(e) => setText(e.target.value)} />
        </div>

        <label className="flex items-start gap-2.5 rounded-lg bg-sunk/60 px-3 py-2.5">
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

        <div className="flex items-center justify-between">
          <span className="text-xs text-muted">
            {edited ? 'Editado por ti' : 'El huésped ya recibió un aviso de espera'}
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
              {approve.isPending ? 'Enviando…' : 'Responder al huésped'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  )
}
