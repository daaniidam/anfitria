import { useEffect, useState } from 'react'

// Bus de avisos desacoplado de React: cualquier módulo (incluido el QueryClient)
// puede lanzar un aviso con notify(), y <ToastHost/> los pinta.
type ToastKind = 'success' | 'error' | 'info'
interface Toast {
  id: number
  message: string
  kind: ToastKind
}

type Listener = (toasts: Toast[]) => void

let toasts: Toast[] = []
const listeners = new Set<Listener>()
let nextId = 1

function emit() {
  for (const l of listeners) l(toasts)
}

export function notify(message: string, kind: ToastKind = 'info') {
  const id = nextId++
  toasts = [...toasts, { id, message, kind }]
  emit()
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    emit()
  }, 3500)
}

const STYLES: Record<ToastKind, string> = {
  success: 'border-brand/30 bg-brand text-white',
  error: 'border-transparent bg-warn text-white',
  info: 'border-line bg-surface text-ink',
}

export function ToastHost() {
  const [items, setItems] = useState<Toast[]>(toasts)
  useEffect(() => {
    listeners.add(setItems)
    return () => {
      listeners.delete(setItems)
    }
  }, [])

  if (items.length === 0) return null
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          role="status"
          className={
            'pointer-events-auto max-w-xs rounded-lg border px-4 py-2.5 text-sm shadow-lg ' +
            STYLES[t.kind]
          }
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
