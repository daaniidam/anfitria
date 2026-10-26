import { Tabs } from '../components/Tabs'
import { ConfiguracionPage } from './ConfiguracionPage'
import { EquipoPage } from './EquipoPage'

export function AjustesPage() {
  return (
    <Tabs
      tabs={[
        { key: 'configuracion', label: 'Puesta en marcha', render: () => <ConfiguracionPage /> },
        { key: 'equipo', label: 'Equipo', render: () => <EquipoPage /> },
      ]}
    />
  )
}
