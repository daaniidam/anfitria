import { Tabs } from '../components/Tabs'
import { BuildingsPage } from './BuildingsPage'
import { PropertiesPage } from './PropertiesPage'
import { ReservasPage } from './ReservasPage'

export function AlojamientosPage() {
  return (
    <Tabs
      tabs={[
        { key: 'pisos', label: 'Pisos', render: () => <PropertiesPage /> },
        { key: 'reservas', label: 'Reservas', render: () => <ReservasPage /> },
        { key: 'edificios', label: 'Edificios', render: () => <BuildingsPage /> },
      ]}
    />
  )
}
