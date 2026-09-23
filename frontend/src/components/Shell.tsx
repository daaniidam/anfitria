import { useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink, useNavigate } from 'react-router-dom'

import { NotificationsApi } from '../api/endpoints'
import { useAuth } from '../auth'

const NAV = [
  { to: '/', label: 'Escaladas', end: true },
  { to: '/metricas', label: 'Métricas', end: false },
  { to: '/pisos', label: 'Pisos', end: false },
  { to: '/edificios', label: 'Edificios', end: false },
  { to: '/auditoria', label: 'Auditoría', end: false },
  { to: '/simulador', label: 'Simulador de huésped', end: false },
]

function NotificationsBell() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: NotificationsApi.list,
    refetchInterval: 20_000,
  })
  const unread = notifications?.filter((n) => !n.read).length ?? 0

  const markAll = useMutation({
    mutationFn: NotificationsApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface text-ink transition hover:bg-sunk"
        aria-label={`Avisos${unread ? ` (${unread} sin leer)` : ''}`}
      >
        <span aria-hidden className="text-base">🔔</span>
        {unread > 0 ? (
          <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-brass px-1 text-[10px] font-bold text-white">
            {unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div className="absolute right-0 top-11 z-20 w-80 rounded-xl border border-line bg-surface p-2 shadow-lg">
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="eyebrow text-brand-ink">Avisos</span>
            {unread > 0 ? (
              <button
                onClick={() => markAll.mutate()}
                className="text-xs font-medium text-brand-ink hover:underline"
              >
                Marcar todo leído
              </button>
            ) : null}
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {notifications && notifications.length > 0 ? (
              notifications.slice(0, 12).map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => {
                      setOpen(false)
                      navigate('/')
                    }}
                    className={
                      'w-full rounded-lg px-2 py-2 text-left text-sm transition hover:bg-sunk ' +
                      (n.read ? 'text-muted' : 'text-ink')
                    }
                  >
                    <span className="mr-1.5 align-middle">
                      {n.read ? '·' : <span className="text-brass">●</span>}
                    </span>
                    {n.message}
                  </button>
                </li>
              ))
            ) : (
              <li className="px-2 py-6 text-center text-sm text-muted">Sin avisos por ahora.</li>
            )}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-ground">
      <header className="sticky top-0 z-10 border-b border-line bg-mist/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-sm font-bold text-white">
              A
            </span>
            <div className="leading-tight">
              <span className="font-display text-lg font-bold text-ink">AnfitrIA</span>
              <span className="ml-2 eyebrow text-muted">conserje supervisado</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <NotificationsBell />
            <span className="hidden text-sm text-muted sm:inline">{user?.name}</span>
            <button
              onClick={() => void logout()}
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-medium text-ink transition hover:bg-sunk"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-6 px-5 py-6">
        <nav className="hidden w-52 shrink-0 md:block">
          <ul className="flex flex-col gap-1">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    'block rounded-lg px-3 py-2 text-sm font-medium transition ' +
                    (isActive
                      ? 'bg-brand-soft text-brand-ink'
                      : 'text-muted hover:bg-sunk hover:text-ink')
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  )
}
