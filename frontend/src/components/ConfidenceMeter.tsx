const SEGMENTS = 10
const AUTO_THRESHOLD = 0.55

/**
 * Medidor de confianza de la IA — el elemento firma de AnfitrIA.
 * Barra segmentada en latón que muestra cuán segura está la respuesta, y avisa
 * cuando supera el umbral de auto-envío.
 */
export function ConfidenceMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const filled = Math.round(value * SEGMENTS)
  const auto = value >= AUTO_THRESHOLD

  return (
    <div className="flex items-center gap-3">
      <div className="flex gap-[3px]" role="img" aria-label={`Confianza ${pct}%`}>
        {Array.from({ length: SEGMENTS }).map((_, i) => (
          <span
            key={i}
            className={`h-4 w-[6px] rounded-[2px] ${i < filled ? 'bg-brass' : 'bg-line'}`}
          />
        ))}
      </div>
      <span className="font-mono text-xs font-medium text-ink">{pct}%</span>
      <span className="eyebrow text-muted">confianza</span>
      {auto ? <span className="eyebrow text-brass-ink">· responde sola</span> : null}
    </div>
  )
}
