import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth'
import { Shell } from './components/Shell'
import { ActividadPage } from './pages/ActividadPage'
import { AjustesPage } from './pages/AjustesPage'
import { AlojamientosPage } from './pages/AlojamientosPage'
import { BandejaPage } from './pages/BandejaPage'
import { GuestSimPage } from './pages/GuestSimPage'
import { HoyPage } from './pages/HoyPage'
import { LoginPage } from './pages/LoginPage'

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
        <Route path="/" element={<HoyPage />} />
        <Route path="/conversaciones" element={<BandejaPage />} />
        <Route path="/alojamientos" element={<AlojamientosPage />} />
        <Route path="/actividad" element={<ActividadPage />} />
        <Route path="/ajustes" element={<AjustesPage />} />
        <Route path="/probar" element={<GuestSimPage />} />

        {/* Rutas antiguas → nueva estructura (por si hay enlaces guardados) */}
        <Route path="/pisos" element={<Navigate to="/alojamientos?tab=pisos" replace />} />
        <Route path="/reservas" element={<Navigate to="/alojamientos?tab=reservas" replace />} />
        <Route path="/edificios" element={<Navigate to="/alojamientos?tab=edificios" replace />} />
        <Route path="/metricas" element={<Navigate to="/actividad?tab=metricas" replace />} />
        <Route path="/auditoria" element={<Navigate to="/actividad?tab=auditoria" replace />} />
        <Route path="/equipo" element={<Navigate to="/ajustes?tab=equipo" replace />} />
        <Route path="/simulador" element={<Navigate to="/probar" replace />} />
        <Route path="/ajustes/simulador" element={<Navigate to="/probar" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  )
}
