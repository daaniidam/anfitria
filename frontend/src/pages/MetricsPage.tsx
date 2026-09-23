import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'

import { MetricsApi } from '../api/endpoints'
import { Card, EmptyState } from '../components/ui'
import type { MetricsPoint } from '../types'

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

          {data.daily.some((d) => d.auto_answered + d.escalated > 0) ? (
            <TrendCard points={data.daily} />
          ) : null}
        </>
      )}
    </div>
  )
}

function TrendCard({ points }: { points: MetricsPoint[] }) {
  const maxTotal = Math.max(1, ...points.map((p) => p.auto_answered + p.escalated))
  const H = 120

  return (
    <Card className="p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="eyebrow block text-muted">Actividad diaria (últimos 14 días)</span>
        <div className="flex gap-4 text-xs text-muted">
          <Legend swatch={TEAL} label="Resueltas por la IA" />
          <Legend swatch={BRASS} label="Escaladas" />
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="flex min-w-[420px] items-end gap-1.5" style={{ height: H }}>
          {points.map((p) => {
            const total = p.auto_answered + p.escalated
            const autoH = (p.auto_answered / maxTotal) * H
            const escH = (p.escalated / maxTotal) * H
            const day = p.date.slice(8) // DD
            return (
              <div key={p.date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="flex w-full max-w-7 flex-col justify-end"
                  style={{ height: H }}
                  role="img"
                  aria-label={`${p.date}: ${p.auto_answered} resueltas, ${p.escalated} escaladas`}
                >
                  {escH > 0 ? (
                    <div
                      title={`${p.date} · escaladas: ${p.escalated}`}
                      style={{ height: escH, background: BRASS }}
                      className="rounded-t-[3px]"
                    />
                  ) : null}
                  {autoH > 0 ? (
                    <div
                      title={`${p.date} · resueltas por la IA: ${p.auto_answered}`}
                      style={{
                        height: autoH,
                        background: TEAL,
                        marginTop: escH > 0 ? 2 : 0,
                      }}
                      className={escH > 0 ? '' : 'rounded-t-[3px]'}
                    />
                  ) : null}
                  {total === 0 ? <div className="h-[3px] rounded bg-line" /> : null}
                </div>
                <span className="font-mono text-[10px] tabular-nums text-muted">{day}</span>
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-2.5 w-2.5 rounded-[2px]"
        style={{ background: swatch }}
      />
      {label}
    </span>
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
