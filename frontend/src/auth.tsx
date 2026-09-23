import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

import { AuthApi } from './api/endpoints'
import type { User } from './types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    async function bootstrap() {
      // La sesión vive en una cookie httpOnly: preguntamos al backend quién somos.
      try {
        const me = await AuthApi.me()
        if (active) setUser(me)
      } catch {
        /* sin sesión */
      }
      if (active) setLoading(false)
    }
    void bootstrap()
    return () => {
      active = false
    }
  }, [])

  async function login(email: string, password: string) {
    await AuthApi.login({ email, password })
    setUser(await AuthApi.me())
  }

  async function register(email: string, name: string, password: string) {
    await AuthApi.register({ email, name, password })
    await login(email, password)
  }

  async function logout() {
    try {
      await AuthApi.logout()
    } catch {
      /* la cookie se limpia igualmente en el servidor */
    }
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return context
}
