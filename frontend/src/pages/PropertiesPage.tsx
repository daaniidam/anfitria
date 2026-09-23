import { useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { BuildingsApi, PropertiesApi } from '../api/endpoints'
import { Button, Card, EmptyState, Field, Tag, TextArea } from '../components/ui'
import type { KnowledgeItem, Property } from '../types'

const CATEGORIES = ['check-in', 'wifi', 'cómo llegar', 'normas', 'recomendaciones', 'general']

export function PropertiesPage() {
  const queryClient = useQueryClient()
  const { data: properties } = useQuery({ queryKey: ['properties'], queryFn: PropertiesApi.list })
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [lang, setLang] = useState('es')
  const [autoAnswer, setAutoAnswer] = useState(true)
  const [buildingId, setBuildingId] = useState<number | ''>('')

  const { data: buildings } = useQuery({ queryKey: ['buildings'], queryFn: BuildingsApi.list })
  const selected = properties?.find((p) => p.id === selectedId) ?? null

  const create = useMutation({
    mutationFn: () =>
      PropertiesApi.create({
        name,
        default_language: lang,
        auto_answer: autoAnswer,
        building_id: buildingId === '' ? null : buildingId,
      }),
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
            {buildings && buildings.length > 0 ? (
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-ink">Edificio (opcional)</span>
                <select
                  value={buildingId}
                  onChange={(e) => setBuildingId(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink focus:border-brand focus:ring-2 focus:ring-brand-soft"
                >
                  <option value="">Sin edificio</option>
                  {buildings.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className="flex items-start gap-2.5 rounded-lg bg-sunk/60 px-3 py-2.5">
              <input
                type="checkbox"
                checked={autoAnswer}
                onChange={(e) => setAutoAnswer(e.target.checked)}
                className="mt-0.5 h-4 w-4 accent-brand"
              />
              <span className="text-sm text-ink">
                Responder automáticamente
                <span className="mt-0.5 block text-xs text-muted">
                  La IA contesta sola cuando está segura; si no, te lo escala.
                </span>
              </span>
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
              <span className="flex items-center gap-1.5">
                <Tag tone={property.auto_answer ? 'brand' : 'muted'}>
                  {property.auto_answer ? 'auto' : 'manual'}
                </Tag>
                <Tag tone="muted">{property.default_language.toUpperCase()}</Tag>
              </span>
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
  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['knowledge', property.id] })

  const add = useMutation({
    mutationFn: () => PropertiesApi.addKnowledge(property.id, { category, content }),
    onSuccess: () => {
      setContent('')
      void invalidate()
    },
  })

  const fileRef = useRef<HTMLInputElement>(null)
  const importFile = useMutation({
    mutationFn: (file: File) => PropertiesApi.importKnowledge(property.id, file),
    onSuccess: () => invalidate(),
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
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="brand"
              disabled={add.isPending || content.trim().length === 0}
              onClick={() => add.mutate()}
            >
              {add.isPending ? 'Guardando…' : 'Añadir a la ficha'}
            </Button>
            <span className="text-xs text-muted">o</span>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.pdf,text/csv,application/pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) importFile.mutate(file)
                e.target.value = ''
              }}
            />
            <Button
              variant="ghost"
              disabled={importFile.isPending}
              onClick={() => fileRef.current?.click()}
            >
              {importFile.isPending ? 'Importando…' : 'Importar CSV / PDF'}
            </Button>
          </div>
          {importFile.isSuccess ? (
            <p className="text-xs text-brand-ink">
              Importados {importFile.data.imported} fragmentos a la ficha.
            </p>
          ) : null}
          {importFile.isError ? (
            <p className="text-xs text-warn">
              {(importFile.error as Error).message || 'No se pudo importar el fichero.'}
            </p>
          ) : null}
        </div>
      </Card>

      {items && items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item.id}>
              <KnowledgeCard
                item={item}
                onSave={(content) =>
                  PropertiesApi.updateKnowledge(property.id, item.id, { content }).then(invalidate)
                }
                onDelete={() => PropertiesApi.removeKnowledge(property.id, item.id).then(invalidate)}
              />
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

/** Tarjeta de conocimiento con edición en línea y borrado. Reutilizable en pisos y edificios. */
export function KnowledgeCard({
  item,
  onSave,
  onDelete,
}: {
  item: KnowledgeItem
  onSave: (content: string) => Promise<unknown>
  onDelete: () => Promise<unknown>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(item.content)
  const [busy, setBusy] = useState(false)

  async function run(fn: () => Promise<unknown>) {
    setBusy(true)
    try {
      await fn()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card className="p-3">
      <div className="mb-1 flex items-center gap-2">
        <Tag tone="brass">{item.category}</Tag>
        <div className="ml-auto flex gap-2">
          {editing ? null : (
            <>
              <button
                onClick={() => {
                  setDraft(item.content)
                  setEditing(true)
                }}
                className="text-xs font-medium text-brand-ink hover:underline"
              >
                Editar
              </button>
              <button
                onClick={() => void run(onDelete)}
                disabled={busy}
                className="text-xs font-medium text-muted hover:text-brass-ink hover:underline"
              >
                Borrar
              </button>
            </>
          )}
        </div>
      </div>
      {editing ? (
        <div className="flex flex-col gap-2">
          <TextArea rows={2} value={draft} onChange={(e) => setDraft(e.target.value)} />
          <div className="flex gap-2">
            <Button
              variant="brand"
              disabled={busy || draft.trim().length === 0}
              onClick={() =>
                void run(async () => {
                  await onSave(draft.trim())
                  setEditing(false)
                })
              }
            >
              {busy ? 'Guardando…' : 'Guardar'}
            </Button>
            <Button variant="ghost" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink">{item.content}</p>
      )}
    </Card>
  )
}
