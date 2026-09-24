import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'

import { OnboardingApi } from '../api/endpoints'
import { Card } from './ui'

const HIDE_KEY = 'anfitria_onboarding_hidden'

function readHidden(): boolean {
  try {
    return localStorage.getItem(HIDE_KEY) === '1'
  } catch {
    return false
  }
}

interface Step {
  label: string
  hint: string
  done: boolean
  to: string
  cta: string
}

export function Onboarding() {
  const [hidden, setHidden] = useState(readHidden)
  const { data } = useQuery({ queryKey: ['onboarding'], queryFn: OnboardingApi.status })

  if (!data || hidden) return null

  const steps: Step[] = [
    {
      label: 'Crea tu primer piso',
      hint: 'Cada piso tiene su propia ficha e IA.',
      done: data.has_property,
      to: '/pisos',
      cta: 'Crear piso',
    },
    {
      label: 'Completa la ficha (o impórtala)',
      hint: 'Wifi, check-in, normas… es lo que la IA usa para responder.',
      done: data.has_knowledge,
      to: '/pisos',
      cta: 'Añadir info',
    },
    {
      label: 'Pruébalo con un huésped',
      hint: 'Escribe como si fueras el huésped y mira cómo responde.',
      done: data.has_conversation,
      to: '/simulador',
      cta: 'Abrir simulador',
    },
  ]

  const doneCount = steps.filter((s) => s.done).length
  if (doneCount === steps.length) return null // completado → desaparece solo

  function hide() {
    try {
      localStorage.setItem(HIDE_KEY, '1')
    } catch {
      /* almacenamiento no disponible */
    }
    setHidden(true)
  }

  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="eyebrow text-brand-ink">Primeros pasos</p>
          <h2 className="mt-1 font-display text-lg font-bold text-ink">
            Pon a punto tu conserje en 3 pasos
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-muted">{doneCount}/{steps.length}</span>
          <button onClick={hide} className="text-xs text-muted hover:text-ink hover:underline">
            Ocultar
          </button>
        </div>
      </div>

      <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-sunk">
        <div
          className="h-full rounded-full bg-brand transition-all"
          style={{ width: `${(doneCount / steps.length) * 100}%` }}
        />
      </div>

      <ol className="flex flex-col gap-2">
        {steps.map((step, i) => (
          <li
            key={step.to + i}
            className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2.5"
          >
            <span
              className={
                'grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ' +
                (step.done ? 'bg-brand text-white' : 'border border-line text-muted')
              }
            >
              {step.done ? '✓' : i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className={'text-sm font-medium ' + (step.done ? 'text-muted line-through' : 'text-ink')}>
                {step.label}
              </p>
              {!step.done ? <p className="text-xs text-muted">{step.hint}</p> : null}
            </div>
            {!step.done ? (
              <NavLink
                to={step.to}
                className="shrink-0 rounded-lg bg-brand-soft px-3 py-1.5 text-xs font-medium text-brand-ink transition hover:brightness-95"
              >
                {step.cta}
              </NavLink>
            ) : null}
          </li>
        ))}
      </ol>

      {!data.has_whatsapp ? (
        <p className="mt-3 text-xs text-muted">
          Opcional: conecta el WhatsApp del negocio desde <b>Pisos</b> cuando quieras. La demo
          funciona sin claves.
        </p>
      ) : null}
    </Card>
  )
}
