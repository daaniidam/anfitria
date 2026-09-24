import { useState, type FormEvent, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'

import { PropertiesApi, WhatsAppApi } from '../api/endpoints'
import { notify } from '../components/Toast'
import { Button, Card, Field, Tag } from '../components/ui'

const TEMPLATES = [
  { name: 'bienvenida', text: 'Hola {{nombre}}, soy el conserje de {{alojamiento}}. ¿En qué te ayudo?' },
  { name: 'aviso_espera', text: 'Lo confirmo con el anfitrión y te respondo enseguida. 🙌' },
  { name: 'checkin', text: 'Tu check-in es el {{fecha}} a partir de las {{hora}}. ¡Buen viaje!' },
]

export function WhatsAppSetupPage() {
  const queryClient = useQueryClient()
  const { data: status } = useQuery({ queryKey: ['whatsapp'], queryFn: WhatsAppApi.status })
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['whatsapp'] })
    void queryClient.invalidateQueries({ queryKey: ['properties'] })
    void queryClient.invalidateQueries({ queryKey: ['onboarding'] })
  }

  const [business, setBusiness] = useState('')
  const [phone, setPhone] = useState('')

  const connect = useMutation({
    mutationFn: () => WhatsAppApi.connect({ business_name: business, phone }),
    onSuccess: () => {
      notify('Número verificado y conectado.', 'success')
      invalidate()
    },
  })
  const disconnect = useMutation({ mutationFn: WhatsAppApi.disconnect, onSuccess: invalidate })
  const approve = useMutation({
    mutationFn: WhatsAppApi.approveTemplates,
    onSuccess: () => {
      notify('Plantillas aprobadas.', 'success')
      invalidate()
    },
  })
  const assign = useMutation({
    mutationFn: (id: number) => WhatsAppApi.assign(id),
    onSuccess: invalidate,
  })

  const connected = status?.connected ?? false
  const templates = status?.templates_approved ?? false
  const assigned = (status?.pisos_assigned ?? 0) > 0

  function onConnect(e: FormEvent) {
    e.preventDefault()
    if (business.trim() && phone.trim()) connect.mutate()
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Canal</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Conecta WhatsApp Business</h1>
        <p className="mt-1 text-sm text-muted">
          Cuatro pasos para que la IA atienda a tus huéspedes por WhatsApp. La verificación con
          Meta está simulada en esta demo.
        </p>
      </header>

      <Step n={1} title="Conecta tu número" done={connected}>
        {connected ? (
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-ink">{status?.phone}</span>
            <Tag tone="brand">verificado</Tag>
            <button
              onClick={() => disconnect.mutate()}
              className="text-xs text-muted hover:text-ink hover:underline"
            >
              Desconectar
            </button>
          </div>
        ) : (
          <form onSubmit={onConnect} className="flex flex-col gap-3 sm:max-w-md">
            <Field label="Nombre del negocio" placeholder="p. ej. Apartamentos Sol" value={business} onChange={(e) => setBusiness(e.target.value)} />
            <Field label="Teléfono de WhatsApp Business" placeholder="+34 600 11 22 33" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <Button variant="brand" type="submit" disabled={connect.isPending} className="self-start">
              {connect.isPending ? 'Verificando…' : 'Verificar y conectar'}
            </Button>
          </form>
        )}
      </Step>

      <Step n={2} title="Aprueba las plantillas" done={templates} locked={!connected}>
        <ul className="mb-3 flex flex-col gap-1.5">
          {TEMPLATES.map((t) => (
            <li key={t.name} className="rounded-lg border border-line bg-surface px-3 py-2 text-sm">
              <span className="mr-2 font-mono text-xs text-brass-ink">{t.name}</span>
              <span className="text-muted">{t.text}</span>
            </li>
          ))}
        </ul>
        {templates ? (
          <Tag tone="brand">plantillas aprobadas</Tag>
        ) : (
          <Button variant="brand" disabled={approve.isPending || !connected} onClick={() => approve.mutate()}>
            {approve.isPending ? 'Aprobando…' : 'Aprobar plantillas'}
          </Button>
        )}
      </Step>

      <Step n={3} title="Activa WhatsApp en tus pisos" done={assigned} locked={!templates}>
        {properties && properties.length > 0 ? (
          <ul className="flex flex-col gap-1.5">
            {properties.map((p) => (
              <li key={p.id} className="flex items-center justify-between rounded-lg border border-line bg-surface px-3 py-2">
                <span className="text-sm font-medium text-ink">{p.name}</span>
                {p.whatsapp_phone_number_id ? (
                  <Tag tone="brand">activo</Tag>
                ) : (
                  <button
                    onClick={() => assign.mutate(p.id)}
                    disabled={!templates || assign.isPending}
                    className="text-xs font-medium text-brand-ink hover:underline disabled:opacity-50"
                  >
                    Activar WhatsApp
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">Crea un piso primero en Alojamientos.</p>
        )}
      </Step>

      <Step n={4} title="Pruébalo" done={false} locked={!assigned}>
        <p className="mb-2 text-sm text-muted">
          Todo listo. Escribe como si fueras el huésped y comprueba que la IA responde.
        </p>
        <NavLink
          to="/ajustes?tab=simulador"
          className="inline-flex rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white transition hover:bg-brand-ink"
        >
          Abrir el simulador →
        </NavLink>
      </Step>
    </div>
  )
}

function Step({
  n,
  title,
  done,
  locked,
  children,
}: {
  n: number
  title: string
  done: boolean
  locked?: boolean
  children: ReactNode
}) {
  return (
    <Card className={'p-4 ' + (locked ? 'opacity-55' : '')}>
      <div className="mb-3 flex items-center gap-3">
        <span
          className={
            'grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold ' +
            (done ? 'bg-brand text-white' : 'border border-line text-muted')
          }
        >
          {done ? '✓' : n}
        </span>
        <h2 className="font-display text-lg font-bold text-ink">{title}</h2>
      </div>
      {children}
    </Card>
  )
}
