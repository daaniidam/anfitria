import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { BuildingsApi } from '../api/endpoints'
import { Button, Card, EmptyState, Field, TextArea } from '../components/ui'
import type { Building } from '../types'
import { KnowledgeCard } from './PropertiesPage'

const CATEGORIES = ['cómo llegar', 'normas', 'parking', 'zonas comunes', 'contacto', 'general']

export function BuildingsPage() {
  const queryClient = useQueryClient()
  const { data: buildings } = useQuery({ queryKey: ['buildings'], queryFn: BuildingsApi.list })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [name, setName] = useState('')

  const selected = buildings?.find((b) => b.id === selectedId) ?? null

  const create = useMutation({
    mutationFn: () => BuildingsApi.create({ name }),
    onSuccess: (building) => {
      setName('')
      setSelectedId(building.id)
      void queryClient.invalidateQueries({ queryKey: ['buildings'] })
    },
  })

  function onCreate(event: FormEvent) {
    event.preventDefault()
    if (name.trim()) create.mutate()
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <div className="flex flex-col gap-4">
        <header>
          <p className="eyebrow text-brand-ink">Grupos de pisos</p>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">Edificios</h1>
          <p className="mt-1 text-sm text-muted">
            El conocimiento de un edificio se comparte con todos sus pisos.
          </p>
        </header>

        <Card className="p-4">
          <form onSubmit={onCreate} className="flex flex-col gap-3">
            <Field
              label="Nombre del edificio"
              placeholder="p. ej. Residencial Sol"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Button variant="brand" type="submit" disabled={create.isPending}>
              {create.isPending ? 'Creando…' : 'Añadir edificio'}
            </Button>
          </form>
        </Card>

        <div className="flex flex-col gap-1.5">
          {buildings?.map((building) => (
            <button
              key={building.id}
              onClick={() => setSelectedId(building.id)}
              className={
                'rounded-lg border px-3 py-2.5 text-left text-sm font-medium transition ' +
                (building.id === selectedId
                  ? 'border-brand bg-brand-soft text-brand-ink'
                  : 'border-line bg-surface text-ink hover:bg-sunk')
              }
            >
              {building.name}
            </button>
          ))}
        </div>
      </div>

      <div>
        {selected ? (
          <SharedKnowledgePanel building={selected} />
        ) : (
          <EmptyState title="Elige o crea un edificio">
            Reúne varios pisos y comparte lo común (cómo llegar, normas del edificio,
            parking, zonas comunes). No tendrás que repetirlo piso por piso.
          </EmptyState>
        )}
      </div>
    </div>
  )
}

function SharedKnowledgePanel({ building }: { building: Building }) {
  const queryClient = useQueryClient()
  const { data: items } = useQuery({
    queryKey: ['building-knowledge', building.id],
    queryFn: () => BuildingsApi.knowledge(building.id),
  })
  const [category, setCategory] = useState('cómo llegar')
  const [content, setContent] = useState('')

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['building-knowledge', building.id] })

  const add = useMutation({
    mutationFn: () => BuildingsApi.addKnowledge(building.id, { category, content }),
    onSuccess: () => {
      setContent('')
      void invalidate()
    },
  })

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Conocimiento compartido</p>
        <h2 className="mt-1 font-display text-xl font-bold text-ink">{building.name}</h2>
      </header>

      <Card className="p-4">
        <div className="flex flex-col gap-3">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-ink">Categoría</span>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <TextArea
            label="Información compartida"
            rows={3}
            placeholder="p. ej. El portal del edificio tiene código 2580. El parking está en la planta -1."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <Button
            variant="brand"
            className="self-start"
            disabled={add.isPending || content.trim().length === 0}
            onClick={() => add.mutate()}
          >
            {add.isPending ? 'Guardando…' : 'Añadir al edificio'}
          </Button>
        </div>
      </Card>

      {items && items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.id}>
              <KnowledgeCard
                item={item}
                onSave={(content) =>
                  BuildingsApi.updateKnowledge(building.id, item.id, { content }).then(invalidate)
                }
                onDelete={() => BuildingsApi.removeKnowledge(building.id, item.id).then(invalidate)}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">
          Aún no hay información compartida. Añade lo común a todos los pisos del edificio.
        </p>
      )}
    </div>
  )
}
