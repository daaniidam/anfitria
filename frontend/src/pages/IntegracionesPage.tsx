import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { IntegrationsApi } from '../api/endpoints'
import { notify } from '../components/Toast'
import { Button, Card, Tag } from '../components/ui'
import type { IntegrationProvider } from '../types'

export function IntegracionesPage() {
  const queryClient = useQueryClient()
  const { data: providers } = useQuery({ queryKey: ['integrations'], queryFn: IntegrationsApi.list })

  const invalidateAll = () => {
    void queryClient.invalidateQueries({ queryKey: ['integrations'] })
    void queryClient.invalidateQueries({ queryKey: ['properties'] })
    void queryClient.invalidateQueries({ queryKey: ['reservations'] })
    void queryClient.invalidateQueries({ queryKey: ['onboarding'] })
  }

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Integraciones</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Conecta tu PMS</h1>
        <p className="mt-1 text-sm text-muted">
          En vez de recrear tu cartera a mano, conéctala: al sincronizar, tus pisos y reservas
          entran solos (y no se duplican al volver a sincronizar).
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-2">
        {providers?.map((p) => (
          <ProviderCard key={p.id} provider={p} onChange={invalidateAll} />
        ))}
      </div>
    </div>
  )
}

function ProviderCard({ provider, onChange }: { provider: IntegrationProvider; onChange: () => void }) {
  const connect = useMutation({
    mutationFn: () => IntegrationsApi.connect(provider.id),
    onSuccess: () => {
      notify(`${provider.name} conectado.`, 'success')
      onChange()
    },
  })
  const disconnect = useMutation({
    mutationFn: () => IntegrationsApi.disconnect(provider.id),
    onSuccess: onChange,
  })
  const sync = useMutation({
    mutationFn: () => IntegrationsApi.sync(provider.id),
    onSuccess: (res) => {
      notify(
        res.properties_imported + res.reservations_imported > 0
          ? `Importados ${res.properties_imported} pisos y ${res.reservations_imported} reservas.`
          : 'Ya estaba todo al día.',
        'success',
      )
      onChange()
    },
  })

  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-sunk font-display font-bold text-ink">
            {provider.name.charAt(0)}
          </span>
          <div>
            <p className="font-medium text-ink">{provider.name}</p>
            {provider.connected ? (
              <p className="text-xs text-muted">{provider.account}</p>
            ) : (
              <p className="text-xs text-muted">PMS / Channel Manager</p>
            )}
          </div>
        </div>
        {provider.connected ? (
          <Tag tone="brand">conectado</Tag>
        ) : provider.available ? null : (
          <Tag tone="muted">próximamente</Tag>
        )}
      </div>

      {!provider.available ? (
        <Button variant="ghost" disabled className="opacity-60">
          Próximamente
        </Button>
      ) : provider.connected ? (
        <div className="flex gap-2">
          <Button variant="brand" disabled={sync.isPending} onClick={() => sync.mutate()}>
            {sync.isPending ? 'Sincronizando…' : 'Sincronizar cartera'}
          </Button>
          <Button variant="ghost" disabled={disconnect.isPending} onClick={() => disconnect.mutate()}>
            Desconectar
          </Button>
        </div>
      ) : (
        <Button variant="brand" disabled={connect.isPending} onClick={() => connect.mutate()}>
          {connect.isPending ? 'Conectando…' : 'Conectar'}
        </Button>
      )}
    </Card>
  )
}
