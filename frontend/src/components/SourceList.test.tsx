import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { SourceList } from './SourceList'
import type { Citation } from '../types'

const citations: Citation[] = [
  { category: 'wifi', content: 'La contraseña del wifi es CASA-1234.', score: 0.91 },
  { category: 'parking', content: 'Parking en la calle Mayor 4.', score: 0.84 },
]

describe('SourceList', () => {
  it('muestra cada fuente con su categoría, contenido y % de similitud', () => {
    render(<SourceList citations={citations} />)
    expect(screen.getByText('wifi')).toBeInTheDocument()
    expect(screen.getByText('La contraseña del wifi es CASA-1234.')).toBeInTheDocument()
    expect(screen.getByText('91%')).toBeInTheDocument()
    expect(screen.getByText('84%')).toBeInTheDocument()
  })

  it('no renderiza nada si no hay fuentes', () => {
    const { container } = render(<SourceList citations={[]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
