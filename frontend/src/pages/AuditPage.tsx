import { useQuery } from '@tanstack/react-query'

import { AuditApi } from '../api/endpoints'
import { Card, EmptyState, Tag } from '../components/ui'
import type { AuditLog } from '../types'

const ACTION_LABEL: Record<string, string> = {
  draft_generated: 'Borrador generado',
  auto_answered: 'Respondió sola',
  escalated: 'Escaló al anfitrión',
  approved_and_sent: 'Aprobado y enviado',
  edited_and_sent: 'Editado y enviado',
  learned: 'Aprendió la respuesta',
}

function actorTone(actor: string): 'brand' | 'brass' {
  return actor === 'ai' ? 'brand' : 'brass'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' })
}

export function AuditPage() {
  const { data: logs } = useQuery({ queryKey: ['audit'], queryFn: AuditApi.list })

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Trazabilidad</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Auditoría</h1>
        <p className="mt-1 text-sm text-muted">
          Qué hizo la IA y qué hiciste tú, y cuándo. IA supervisada, no caja negra.
        </p>
      </header>

      {logs && logs.length > 0 ? (
        <Card className="overflow-hidden p-0">
          <ul className="divide-y divide-line">
            {logs.map((log: AuditLog) => (
              <li key={log.id} className="flex items-center gap-3 px-4 py-3">
                <Tag tone={actorTone(log.actor)}>{log.actor === 'ai' ? 'IA' : 'Anfitrión'}</Tag>
                <span className="flex-1 text-sm text-ink">
                  {ACTION_LABEL[log.action] ?? log.action}
                  {log.detail ? <span className="ml-2 text-xs text-muted">{log.detail}</span> : null}
                </span>
                <span className="shrink-0 font-mono text-xs text-muted">
                  {formatDate(log.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : (
        <EmptyState title="Aún no hay actividad">
          Cuando lleguen mensajes de huéspedes, aquí verás cada decisión de la IA y cada
          respuesta tuya, con su hora.
        </EmptyState>
      )}
    </div>
  )
}
