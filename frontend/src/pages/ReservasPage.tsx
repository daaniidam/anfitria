import { useMemo, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { PropertiesApi, ReservationsApi } from '../api/endpoints'
import { Button, Card, ConfirmButton, EmptyState, Field } from '../components/ui'
import { notify } from '../components/Toast'
import type { ReservationListItem } from '../types'

const SOURCES: Record<string, { label: string; bg: string; fg: string }> = {
  booking: { label: 'Booking', bg: '#e7effb', fg: '#0b4aa2' },
  airbnb: { label: 'Airbnb', bg: '#ffe4ea', fg: '#c31f45' },
  direct: { label: 'Directa', bg: 'var(--brand-soft, #dcece8)', fg: '#0a544b' },
  other: { label: 'Otro', bg: '#eceae2', fg: '#5c6f66' },
}

function SourceBadge({ source }: { source: string }) {
  const s = SOURCES[source] ?? SOURCES.other
  return (
    <span
      className="inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[0.68rem] font-medium"
      style={{ background: s.bg, color: s.fg }}
    >
      {s.label}
    </span>
  )
}

function phaseOf(res: ReservationListItem): { label: string; cls: string } {
  if (res.status === 'cancelled') return { label: 'cancelada', cls: 'bg-sunk text-muted' }
  const today = new Date().toISOString().slice(0, 10)
  if (today < res.check_in) return { label: 'pre-llegada', cls: 'bg-brass-soft text-brass-ink' }
  if (today <= res.check_out) return { label: 'alojado ahora', cls: 'bg-brand-soft text-brand-ink' }
  return { label: 'pasada', cls: 'bg-sunk text-muted' }
}

function fmt(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
}

export function ReservasPage() {
  const queryClient = useQueryClient()
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const { data: reservations } = useQuery({ queryKey: ['reservations'], queryFn: ReservationsApi.list })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['reservations'] })

  const [filter, setFilter] = useState<number | 'all'>('all')
  const shown = useMemo(
    () => (reservations ?? []).filter((r) => filter === 'all' || r.property_id === filter),
    [reservations, filter],
  )

  const remove = useMutation({ mutationFn: (id: number) => ReservationsApi.remove(id), onSuccess: invalidate })

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="flex flex-col gap-4">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="eyebrow text-brand-ink">Estancias</p>
            <h1 className="mt-1 font-display text-2xl font-bold text-ink">Reservas</h1>
            <p className="mt-1 text-sm text-muted">
              Todas las reservas de tus pisos y de dónde vienen. La IA sabe la fase de cada estancia.
            </p>
          </div>
          <label className="text-sm">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
            >
              <option value="all">Todos los pisos</option>
              {properties?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </label>
        </header>

        {shown.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {shown.map((res) => {
              const phase = phaseOf(res)
              return (
                <li key={res.id}>
                  <Card className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3.5">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-ink">{res.guest_name}</span>
                        <SourceBadge source={res.source} />
                        <span className={'inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[0.68rem] ' + phase.cls}>
                          {phase.label}
                        </span>
                      </div>
                      <p className="mt-0.5 text-sm text-muted">
                        <span className="text-ink">{res.property_name}</span> · {fmt(res.check_in)} → {fmt(res.check_out)}
                        {res.guest_ref ? ` · ${res.guest_ref}` : ''}
                        {res.code ? ` · ${res.code}` : ''}
                      </p>
                    </div>
                    <ConfirmButton
                      onConfirm={() => remove.mutate(res.id)}
                      question="¿Borrar la reserva?"
                    />
                  </Card>
                </li>
              )
            })}
          </ul>
        ) : (
          <EmptyState title="Aún no hay reservas">
            Añade una a mano o importa el calendario (.ics) de Booking/Airbnb de un piso.
          </EmptyState>
        )}
      </div>

      <div className="flex flex-col gap-4">
        {properties && properties.length > 0 ? (
          <>
            <CreateReservation propertyIds={properties.map((p) => ({ id: p.id, name: p.name }))} onDone={invalidate} />
            <ImportIcs propertyIds={properties.map((p) => ({ id: p.id, name: p.name }))} onDone={invalidate} />
          </>
        ) : (
          <Card className="p-4">
            <p className="text-sm text-muted">Crea un piso para poder añadir reservas.</p>
          </Card>
        )}
      </div>
    </div>
  )
}

function CreateReservation({
  propertyIds,
  onDone,
}: {
  propertyIds: { id: number; name: string }[]
  onDone: () => void
}) {
  const [pid, setPid] = useState<number>(propertyIds[0].id)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [source, setSource] = useState('direct')

  const create = useMutation({
    mutationFn: () =>
      ReservationsApi.create(pid, {
        guest_name: name,
        guest_ref: phone,
        check_in: checkIn,
        check_out: checkOut,
        source,
      }),
    onSuccess: () => {
      setName('')
      setPhone('')
      setCheckIn('')
      setCheckOut('')
      onDone()
    },
  })
  const valid = name.trim() && phone.trim() && checkIn && checkOut && checkOut >= checkIn

  function onCreate(event: FormEvent) {
    event.preventDefault()
    if (valid) create.mutate()
  }

  const selectCls =
    'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft'

  return (
    <Card className="p-4">
      <p className="eyebrow mb-3 block text-brand-ink">Añadir reserva</p>
      <form onSubmit={onCreate} className="flex flex-col gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-ink">Piso</span>
          <select value={pid} onChange={(e) => setPid(Number(e.target.value))} className={selectCls}>
            {propertyIds.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>
        <Field label="Huésped" placeholder="p. ej. Ana López" value={name} onChange={(e) => setName(e.target.value)} />
        <Field label="Teléfono (WhatsApp)" placeholder="+34 600 12 34 56" value={phone} onChange={(e) => setPhone(e.target.value)} />
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink">Entrada</span>
            <input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} className={selectCls} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink">Salida</span>
            <input type="date" value={checkOut} min={checkIn} onChange={(e) => setCheckOut(e.target.value)} className={selectCls} />
          </label>
        </div>
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-ink">Origen</span>
          <select value={source} onChange={(e) => setSource(e.target.value)} className={selectCls}>
            <option value="direct">Directa</option>
            <option value="booking">Booking</option>
            <option value="airbnb">Airbnb</option>
            <option value="other">Otro</option>
          </select>
        </label>
        <Button variant="brand" type="submit" disabled={!valid || create.isPending}>
          {create.isPending ? 'Guardando…' : 'Añadir reserva'}
        </Button>
      </form>
    </Card>
  )
}

function ImportIcs({
  propertyIds,
  onDone,
}: {
  propertyIds: { id: number; name: string }[]
  onDone: () => void
}) {
  const [pid, setPid] = useState<number>(propertyIds[0].id)
  const fileRef = useRef<HTMLInputElement>(null)
  const importIcs = useMutation({
    mutationFn: (file: File) => ReservationsApi.importIcs(pid, file),
    onSuccess: (res) => {
      notify(`Importadas ${res.imported} reservas de ${res.source}.`, 'success')
      onDone()
    },
  })

  return (
    <Card className="p-4">
      <p className="eyebrow mb-2 block text-brand-ink">Conectar Booking / Airbnb</p>
      <p className="mb-3 text-xs text-muted">
        Sube el calendario <b>.ics</b> que exporta el anuncio; las reservas entran con su origen.
      </p>
      <label className="mb-3 block">
        <select
          value={pid}
          onChange={(e) => setPid(Number(e.target.value))}
          className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
        >
          {propertyIds.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </label>
      <input
        ref={fileRef}
        type="file"
        accept=".ics,text/calendar"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) importIcs.mutate(file)
          e.target.value = ''
        }}
      />
      <Button variant="ghost" className="w-full" disabled={importIcs.isPending} onClick={() => fileRef.current?.click()}>
        {importIcs.isPending ? 'Importando…' : 'Importar calendario (.ics)'}
      </Button>
      {importIcs.isSuccess ? (
        <p className="mt-2 text-xs text-brand-ink">
          Importadas {importIcs.data.imported} reservas de {importIcs.data.source}.
        </p>
      ) : null}
      {importIcs.isError ? (
        <p className="mt-2 text-xs text-warn">{(importIcs.error as Error).message}</p>
      ) : null}
    </Card>
  )
}
