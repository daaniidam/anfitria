import { useState } from 'react'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

type Variant = 'brass' | 'brand' | 'ghost' | 'soft'

const VARIANTS: Record<Variant, string> = {
  brass: 'bg-brass text-white hover:bg-brass-ink focus-visible:outline-brass',
  brand: 'bg-brand text-white hover:bg-brand-ink focus-visible:outline-brand',
  ghost: 'border border-line bg-surface text-ink hover:bg-sunk focus-visible:outline-brand',
  soft: 'bg-brand-soft text-brand-ink hover:brightness-95 focus-visible:outline-brand',
}

export function Button({
  variant = 'brand',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold ' +
        'transition focus-visible:outline-2 focus-visible:outline-offset-2 ' +
        'disabled:cursor-not-allowed disabled:opacity-50 ' +
        `${VARIANTS[variant]} ${className}`
      }
      {...props}
    />
  )
}

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <div className={`rounded-xl border border-line bg-surface ${className}`}>{children}</div>
  )
}

export function Field({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-ink">{label}</span>
      <input
        className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink outline-none placeholder:text-muted/70 focus:border-brand focus:ring-2 focus:ring-brand-soft"
        {...props}
      />
      {hint ? <span className="mt-1 block text-xs text-muted">{hint}</span> : null}
    </label>
  )
}

export function TextArea({
  label,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }) {
  return (
    <label className="block">
      {label ? <span className="mb-1 block text-sm font-medium text-ink">{label}</span> : null}
      <textarea
        className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm leading-relaxed text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand-soft"
        {...props}
      />
    </label>
  )
}

export function Tag({ children, tone = 'brand' }: { children: ReactNode; tone?: 'brand' | 'brass' | 'muted' }) {
  const tones = {
    brand: 'bg-brand-soft text-brand-ink',
    brass: 'bg-brass-soft text-brass-ink',
    muted: 'bg-sunk text-muted',
  }
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[0.68rem] ${tones[tone]}`}>
      {children}
    </span>
  )
}

/** Botón de borrado con confirmación en línea (sin diálogos): "Borrar" → "¿Seguro? Sí / No". */
export function ConfirmButton({
  onConfirm,
  label = 'Borrar',
  question = '¿Seguro?',
}: {
  onConfirm: () => void
  label?: string
  question?: string
}) {
  const [armed, setArmed] = useState(false)
  if (armed) {
    return (
      <span className="inline-flex items-center gap-2 text-xs">
        <span className="text-muted">{question}</span>
        <button
          onClick={() => {
            setArmed(false)
            onConfirm()
          }}
          className="font-medium text-brass-ink hover:underline"
        >
          Sí
        </button>
        <button onClick={() => setArmed(false)} className="text-muted hover:underline">
          No
        </button>
      </span>
    )
  }
  return (
    <button
      onClick={() => setArmed(true)}
      className="text-xs font-medium text-muted hover:text-brass-ink hover:underline"
    >
      {label}
    </button>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-sunk/50 px-6 py-12 text-center">
      <p className="font-display text-lg text-ink">{title}</p>
      {children ? <p className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</p> : null}
    </div>
  )
}
