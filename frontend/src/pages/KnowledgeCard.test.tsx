import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { KnowledgeCard } from './PropertiesPage'
import type { KnowledgeItem } from '../types'

const item: KnowledgeItem = { id: 1, category: 'wifi', content: 'Clave: CASA-1234' }

describe('KnowledgeCard', () => {
  it('muestra la información y permite editarla', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn().mockResolvedValue(undefined)
    const onDelete = vi.fn().mockResolvedValue(undefined)

    render(<KnowledgeCard item={item} onSave={onSave} onDelete={onDelete} />)

    expect(screen.getByText('Clave: CASA-1234')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Editar' }))
    const textarea = screen.getByRole('textbox')
    await user.clear(textarea)
    await user.type(textarea, 'Clave nueva: SOL-9999')
    await user.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(onSave).toHaveBeenCalledWith('Clave nueva: SOL-9999')
  })

  it('borra al pulsar Borrar', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn().mockResolvedValue(undefined)
    const onDelete = vi.fn().mockResolvedValue(undefined)

    render(<KnowledgeCard item={item} onSave={onSave} onDelete={onDelete} />)
    await user.click(screen.getByRole('button', { name: 'Borrar' }))

    expect(onDelete).toHaveBeenCalledTimes(1)
  })
})
