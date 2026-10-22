import type { Citation } from '../types'
import { Tag } from './ui'

/**
 * RAG visible: muestra en qué fragmentos de la ficha se ancló la IA, con su
 * categoría y el % de similitud. Convierte "confía, es RAG" en "míralo".
 */
export function SourceList({ citations }: { citations: Citation[] }) {
  if (!citations?.length) return null

  return (
    <div className="rounded-xl border border-line bg-sunk p-3">
      <p className="eyebrow text-muted">🔎 La IA se basó en la ficha del piso</p>
      <ul className="mt-2 flex flex-col gap-2.5">
        {citations.map((c, i) => {
          const pct = Math.round(c.score * 100)
          return (
            <li key={i} className="flex flex-col gap-1">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  <Tag tone="muted">{c.category}</Tag>
                  <span className="text-sm text-ink">{c.content}</span>
                </div>
                <span className="shrink-0 font-mono text-xs font-medium text-brass-ink">{pct}%</span>
              </div>
              <div
                className="h-1.5 w-full overflow-hidden rounded-full bg-line"
                role="img"
                aria-label={`Similitud ${pct}%`}
              >
                <span className="block h-full rounded-full bg-brass" style={{ width: `${pct}%` }} />
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
