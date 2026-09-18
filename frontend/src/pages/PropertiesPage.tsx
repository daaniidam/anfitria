import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { PropertiesApi } from '../api/endpoints'
import { Button, Card, EmptyState, Field, Tag, TextArea } from '../components/ui'
import type { Property } from '../types'

const CATEGORIES = ['check-in', 'wifi', 'cómo llegar', 'normas', 'recomendaciones', 'general']

export function PropertiesPage() {
  const queryClient = useQueryClient()
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [lang, setLang] = useState('es')

  const selected = properties?.find((p) => p.id === selectedId) ?? null

  const create = useMutation({
    mutationFn: () => PropertiesApi.create({ name, default_language: lang }),
    onSuccess: (property) => {
      setName('')
      setSelectedId(property.id)
      void queryClient.invalidateQueries({ queryKey: ['properties'] })
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
          <p className="eyebrow text-brand-ink">Tus alojamientos</p>
          <h1 className="mt-1 font-display text-2xl font-bold text-ink">Pisos</h1>
        </header>

        <Card className="p-4">
          <form onSubmit={onCreate} className="flex flex-col gap-3">
            <Field
              label="Nombre del piso"
              placeholder="p. ej. Ático Malasaña"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-ink">Idioma por defecto</span>
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
              >
                <option value="es">Español</option>
                <option value="en">Inglés</option>
              </select>
            </label>
            <Button variant="brand" type="submit" disabled={create.isPending}>
              {create.isPending ? 'Creando…' : 'Añadir piso'}
            </Button>
          </form>
        </Card>

        <div className="flex flex-col gap-1.5">
          {properties?.map((property) => (
            <button
              key={property.id}
              onClick={() => setSelectedId(property.id)}
              className={
                'flex items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm transition ' +
                (property.id === selectedId
                  ? 'border-brand bg-brand-soft text-brand-ink'
                  : 'border-line bg-surface text-ink hover:bg-sunk')
              }
            >
              <span className="font-medium">{property.name}</span>
              <Tag tone="muted">{property.default_language.toUpperCase()}</Tag>
            </button>
          ))}
        </div>
      </div>

      <div>
        {selected ? (
          <KnowledgePanel property={selected} />
        ) : (
          <EmptyState title="Elige o crea un piso">
            Cada piso tiene su propia ficha de conocimiento (wifi, check-in, cómo
            llegar…). Es lo que la IA usa para responder a los huéspedes.
          </EmptyState>
        )}
      </div>
    </div>
  )
}

function KnowledgePanel({ property }: { property: Property }) {
  const queryClient = useQueryClient()
  const { data: items } = useQuery({
    queryKey: ['knowledge', property.id],
    queryFn: () => PropertiesApi.knowledge(property.id),
  })
  const [category, setCategory] = useState('wifi')
  const [content, setContent] = useState('')

  const add = useMutation({
    mutationFn: () => PropertiesApi.addKnowledge(property.id, { category, content }),
    onSuccess: () => {
      setContent('')
      void queryClient.invalidateQueries({ queryKey: ['knowledge', property.id] })
    },
  })

  return (
    <div className="flex flex-col gap-4">
      <header>
        <p className="eyebrow text-brand-ink">Ficha de conocimiento</p>
        <h2 className="mt-1 font-display text-xl font-bold text-ink">{property.name}</h2>
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
            label="Información"
            rows={3}
            placeholder="p. ej. La contraseña del wifi es CASA-1234. El router está en el salón."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
          <Button
            variant="brand"
            className="self-start"
            disabled={add.isPending || content.trim().length === 0}
            onClick={() => add.mutate()}
          >
            {add.isPending ? 'Guardando…' : 'Añadir a la ficha'}
          </Button>
        </div>
      </Card>

      {items && items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.id}>
              <Card className="p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Tag tone="brass">{item.category}</Tag>
                </div>
                <p className="text-sm text-ink">{item.content}</p>
              </Card>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted">
          Aún no hay información. Añade lo que más te preguntan los huéspedes.
        </p>
      )}
    </div>
  )
}
