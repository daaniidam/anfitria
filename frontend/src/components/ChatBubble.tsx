export function ChatBubble({
  direction,
  text,
  tag,
}: {
  direction: 'in' | 'out'
  text: string
  tag?: string
}) {
  const isGuest = direction === 'in'
  return (
    <div className={`flex ${isGuest ? 'justify-start' : 'justify-end'}`}>
      <div
        className={
          'max-w-[80%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed shadow-sm ' +
          (isGuest
            ? 'rounded-bl-sm bg-surface text-ink ring-1 ring-line'
            : 'rounded-br-sm bg-brand text-white')
        }
      >
        {tag ? (
          <span className={`eyebrow mb-1 block ${isGuest ? 'text-muted' : 'text-brand-soft'}`}>
            {tag}
          </span>
        ) : null}
        <span className="whitespace-pre-wrap">{text}</span>
      </div>
    </div>
  )
}
