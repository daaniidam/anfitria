import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'

import { MetricsApi } from '../api/endpoints'
import { Card, EmptyState } from '../components/ui'

// Colores de datos validados (dataviz): teal ↔ latón, separables para daltonismo.
const TEAL = '#0E8C7E'
const BRASS = '#B4791F'

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

export function MetricsPage() {
  const { data, isLoading } = useQuery({ queryKey: ['metrics'], queryFn: MetricsApi.get })

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="eyebrow text-brand-ink">Rendimiento</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Métricas</h1>
        <p className="mt-1 text-sm text-muted">Cuánto está resolviendo la IA por su cuenta.</p>
      </header>

      {isLoading ? (
        <p className="text-sm text-muted">Cargando…</p>
      ) : !data || (data.conversations === 0 && data.messages_in === 0) ? (
        <EmptyState title="Aún no hay actividad">
          Cuando los huéspedes empiecen a escribir, verás aquí cuánto resuelve la
          IA sola, cuánto se escala y el tiempo ahorrado. Prueba el simulador.
        </EmptyState>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Tile
              label="Resueltas por la IA"
              value={`${Math.round(data.auto_rate * 100)}%`}
              sub="de las gestionadas"
              tone="brand"
            />
            <Tile
              label="Mensajes atendidos"
              value={data.messages_out}
              sub={`${data.conversations} conversaciones`}
            />
            <Tile
              label="Escaladas pendientes"
              value={data.pending}
              sub="esperan al anfitrión"
              tone={data.pending > 0 ? 'warn' : 'ink'}
            />
            <Tile
              label="Tiempo ahorrado"
              value={formatMinutes(data.minutes_saved)}
              sub="≈ 3 min por respuesta"
            />
          </div>

          {data.auto_answered + data.escalated > 0 ? (
            <ProportionCard auto={data.auto_answered} escalated={data.escalated} />
          ) : null}
        </>
      )}
    </div>
  )
}

function Tile({
  label,
  value,
  sub,
  tone = 'ink',
}: {
  label: string
  value: ReactNode
  sub?: string
  tone?: 'ink' | 'brand' | 'warn'
}) {
  const color = tone === 'brand' ? 'text-brand' : tone === 'warn' ? 'text-warn' : 'text-ink'
  return (
    <Card className="p-4">
      <span className="eyebrow block text-muted">{label}</span>
      <div className={`mt-1.5 font-display text-3xl font-bold tabular-nums ${color}`}>{value}</div>
      {sub ? <span className="mt-1 block text-xs text-muted">{sub}</span> : null}
    </Card>
  )
}

function ProportionCard({ auto, escalated }: { auto: number; escalated: number }) {
  const total = auto + escalated
  const autoPct = Math.round((auto / total) * 100)
  const escPct = 100 - autoPct

  return (
    <Card className="p-4">
      <span className="eyebrow mb-3 block text-muted">Reparto de mensajes gestionados</span>

      <div
        className="flex h-7 w-full overflow-hidden rounded-lg"
        role="img"
        aria-label={`Resueltas por la IA ${autoPct}%, escaladas ${escPct}%`}
      >
        <div
          title={`Resueltas por la IA: ${auto} (${autoPct}%)`}
          style={{ width: `${autoPct}%`, background: TEAL }}
          className="h-full"
        />
        <div
          title={`Escaladas: ${escalated} (${escPct}%)`}
          style={{ width: `${escPct}%`, background: BRASS, marginLeft: '2px' }}
          className="h-full"
        />
      </div>

      <table className="mt-4 w-full text-sm">
        <tbody>
          <Row swatch={TEAL} label="Resueltas por la IA" count={auto} pct={autoPct} />
          <Row swatch={BRASS} label="Escaladas al anfitrión" count={escalated} pct={escPct} />
        </tbody>
      </table>
    </Card>
  )
}

function Row({
  swatch,
  label,
  count,
  pct,
}: {
  swatch: string
  label: string
  count: number
  pct: number
}) {
  return (
    <tr className="border-t border-line first:border-t-0">
      <td className="py-1.5">
        <span
          className="mr-2 inline-block h-2.5 w-2.5 rounded-[2px] align-middle"
          style={{ background: swatch }}
        />
        <span className="text-ink">{label}</span>
      </td>
      <td className="py-1.5 text-right font-mono tabular-nums text-ink">{count}</td>
      <td className="w-14 py-1.5 text-right font-mono tabular-nums text-muted">{pct}%</td>
    </tr>
  )
}
