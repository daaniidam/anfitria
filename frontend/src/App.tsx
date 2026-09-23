import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth'
import { Shell } from './components/Shell'
import { BuildingsPage } from './pages/BuildingsPage'
import { GuestSimPage } from './pages/GuestSimPage'
import { InboxPage } from './pages/InboxPage'
import { LoginPage } from './pages/LoginPage'
import { MetricsPage } from './pages/MetricsPage'
import { PropertiesPage } from './pages/PropertiesPage'

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center text-muted">
        <span className="eyebrow">Abriendo el escritorio…</span>
      </div>
    )
  }

  if (!user) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    )
  }

  return (
    <Shell>
      <Routes>
        <Route path="/" element={<InboxPage />} />
        <Route path="/metricas" element={<MetricsPage />} />
        <Route path="/pisos" element={<PropertiesPage />} />
        <Route path="/edificios" element={<BuildingsPage />} />
        <Route path="/simulador" element={<GuestSimPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}
