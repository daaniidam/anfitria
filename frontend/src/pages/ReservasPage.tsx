import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { PropertiesApi, ReservationsApi } from '../api/endpoints'
import { Button, Card, EmptyState, Field, Tag } from '../components/ui'
import type { Property, Reservation } from '../types'

function phaseOf(res: Reservation): { label: string; tone: 'brand' | 'brass' | 'muted' } {
  if (res.status === 'cancelled') return { label: 'cancelada', tone: 'muted' }
  const today = new Date().toISOString().slice(0, 10)
  if (today < res.check_in) return { label: 'pre-llegada', tone: 'brass' }
  if (today <= res.check_out) return { label: 'alojado ahora', tone: 'brand' }
  return { label: 'pasada', tone: 'muted' }
}

function fmt(iso: string): string {
  return new Date(iso + 'T00:00:00').toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function ReservasPage() {
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const selected = properties?.find((p) => p.id === selectedId) ?? properties?.[0] ?? null

  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <div className="flex flex-col gap-4">
        <header>
          <p className="eyebrow text-brand-ink">Estancias</p>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">Reservas</h1>
          <p className="mt-1 text-sm text-muted">
            Con las reservas, la IA sabe la fase de la estancia y responde con fechas concretas.
          </p>
        </header>
        <div className="flex flex-col gap-1.5">
          {properties?.map((property) => (
            <button
              key={property.id}
              onClick={() => setSelectedId(property.id)}
              className={
                'rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition ' +
                (property.id === selected?.id
                  ? 'border-brand bg-brand-soft text-brand-ink'
                  : 'border-line bg-surface text-ink hover:bg-sunk')
              }
            >
              {property.name}
            </button>
          ))}
        </div>
      </div>

      <div>
        {selected ? (
          <ReservationsPanel property={selected} />
        ) : (
          <EmptyState title="Primero crea un piso">
            Las reservas se asignan a un piso. Crea uno en la sección Pisos.
          </EmptyState>
        )}
      </div>
    </div>
  )
}

function ReservationsPanel({ property }: { property: Property }) {
  const queryClient = useQueryClient()
  const { data: reservations } = useQuery({
    queryKey: ['reservations', property.id],
    queryFn: () => ReservationsApi.byProperty(property.id),
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['reservations', property.id] })

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [code, setCode] = useState('')

  const create = useMutation({
    mutationFn: () =>
      ReservationsApi.create(property.id, {
        guest_name: name,
        guest_ref: phone,
        check_in: checkIn,
        check_out: checkOut,
        code: code || null,
      }),
    onSuccess: () => {
      setName('')
      setPhone('')
      setCheckIn('')
      setCheckOut('')
      setCode('')
      void invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: (id: number) => ReservationsApi.remove(id),
    onSuccess: () => invalidate(),
  })

  const valid = name.trim() && phone.trim() && checkIn && checkOut && checkOut >= checkIn

  function onCreate(event: FormEvent) {
    event.preventDefault()
    if (valid) create.mutate()
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Reservas de</p>
        <h2 className="mt-1 font-display text-xl font-bold text-ink">{property.name}</h2>
      </header>

      <Card className="p-4">
        <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2">
          <Field label="Huésped" placeholder="p. ej. Ana López" value={name} onChange={(e) => setName(e.target.value)} />
          <Field label="Teléfono (WhatsApp)" placeholder="+34 600 12 34 56" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink">Entrada (check-in)</span>
            <input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft" />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink">Salida (check-out)</span>
            <input type="date" value={checkOut} min={checkIn} onChange={(e) => setCheckOut(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft" />
          </label>
          <Field label="Código (opcional)" placeholder="p. ej. HMAB-2291" value={code} onChange={(e) => setCode(e.target.value)} />
          <div className="flex items-end">
            <Button variant="brand" type="submit" disabled={!valid || create.isPending}>
              {create.isPending ? 'Guardando…' : 'Añadir reserva'}
            </Button>
          </div>
        </form>
      </Card>

      {reservations && reservations.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {reservations.map((res) => {
            const phase = phaseOf(res)
            return (
              <li key={res.id}>
                <Card className="flex flex-wrap items-center gap-x-4 gap-y-2 p-3.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-ink">{res.guest_name}</span>
                      <Tag tone={phase.tone}>{phase.label}</Tag>
                    </div>
                    <p className="mt-0.5 text-sm text-muted">
                      {fmt(res.check_in)} → {fmt(res.check_out)} · {res.guest_ref}
                      {res.code ? ` · ${res.code}` : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => remove.mutate(res.id)}
                    className="text-xs font-medium text-muted hover:text-brass-ink hover:underline"
                  >
                    Borrar
                  </button>
                </Card>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="text-sm text-muted">
          Aún no hay reservas. Añade una y la IA sabrá en qué fase está cada huésped.
        </p>
      )}
    </div>
  )
}
