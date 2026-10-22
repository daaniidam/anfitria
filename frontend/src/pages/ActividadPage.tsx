import { Tabs } from '../components/Tabs'
import { AuditPage } from './AuditPage'
import { MetricsPage } from './MetricsPage'

/** Cómo va el conserje: analítica y trazabilidad, fuera del cajón de Ajustes. */
export function ActividadPage() {
  return (
    <Tabs
      tabs={[
        { key: 'metricas', label: 'Métricas', render: () => <MetricsPage /> },
        { key: 'auditoria', label: 'Auditoría', render: () => <AuditPage /> },
      ]}
    />
  )
}
