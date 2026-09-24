import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { BillingApi } from '../api/endpoints'
import { notify } from '../components/Toast'
import { Button, Card } from '../components/ui'
import type { PlanOut } from '../types'

export function FacturacionPage() {
  const queryClient = useQueryClient()
  const { data } = useQuery({ queryKey: ['billing'], queryFn: BillingApi.status })

  const setPlan = useMutation({
    mutationFn: (plan: string) => BillingApi.setPlan(plan),
    onSuccess: (res) => {
      notify(`Plan ${res.plan_name} activado.`, 'success')
      void queryClient.invalidateQueries({ queryKey: ['billing'] })
      void queryClient.invalidateQueries({ queryKey: ['properties'] })
    },
  })

  if (!data) return null
  const used = data.properties_used
  const max = data.max_properties
  const pct = Math.min(100, Math.round((used / max) * 100))
  const atLimit = used >= max

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="eyebrow text-brand-ink">Facturación</p>
        <h1 className="mt-1 font-display text-2xl font-bold text-ink">Tu plan</h1>
        <p className="mt-1 text-sm text-muted">
          El precio es por cartera al mes. El pago está simulado en esta demo, pero el
          límite de pisos se aplica de verdad.
        </p>
      </header>

      <Card className="p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <span className="eyebrow text-muted">Plan actual</span>
            <p className="font-display text-2xl font-bold text-ink">
              {data.plan_name}
              <span className="ml-2 text-base font-medium text-muted">
                {data.price_eur === 0 ? 'gratis' : `${data.price_eur} €/mes`}
              </span>
            </p>
          </div>
          <span className={'font-mono text-sm ' + (atLimit ? 'text-warn' : 'text-muted')}>
            {used} / {max} pisos
          </span>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-sunk">
          <div
            className={'h-full rounded-full ' + (atLimit ? 'bg-warn' : 'bg-brand')}
            style={{ width: `${pct}%` }}
          />
        </div>
        {atLimit ? (
          <p className="mt-2 text-xs text-warn">
            Has alcanzado el límite de tu plan. Sube de plan para añadir más pisos.
          </p>
        ) : null}
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {data.plans.map((p) => (
          <PlanCard key={p.id} plan={p} onSelect={() => setPlan.mutate(p.id)} busy={setPlan.isPending} />
        ))}
      </div>
    </div>
  )
}

function PlanCard({ plan, onSelect, busy }: { plan: PlanOut; onSelect: () => void; busy: boolean }) {
  return (
    <Card className={'flex flex-col gap-3 p-4 ' + (plan.current ? 'border-brand' : '')}>
      <div>
        <p className="font-display text-lg font-bold text-ink">{plan.name}</p>
        <p className="text-sm text-muted">
          {plan.price_eur === 0 ? 'Gratis' : `${plan.price_eur} €/mes`} · hasta {plan.max_properties} pisos
        </p>
      </div>
      {plan.current ? (
        <Button variant="soft" disabled>
          Plan actual
        </Button>
      ) : (
        <Button variant="brand" disabled={busy} onClick={onSelect}>
          Cambiar a este plan
        </Button>
      )}
    </Card>
  )
}
