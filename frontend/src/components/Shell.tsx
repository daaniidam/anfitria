import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '../auth'

const NAV = [
  { to: '/', label: 'Bandeja', end: true },
  { to: '/pisos', label: 'Pisos', end: false },
  { to: '/simulador', label: 'Simulador de huésped', end: false },
]

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
            <span className="hidden text-sm text-muted sm:inline">{user?.name}</span>
            <button
              onClick={logout}
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
