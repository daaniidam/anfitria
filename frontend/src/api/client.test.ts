import { describe, expect, it } from 'vitest'

import { ApiError } from './client'

describe('ApiError', () => {
  it('guarda el status y el mensaje', () => {
    const err = new ApiError(404, 'No encontrado')
    expect(err.status).toBe(404)
    expect(err.message).toBe('No encontrado')
    expect(err).toBeInstanceOf(Error)
  })
})
