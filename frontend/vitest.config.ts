// Config de Vitest separada de vite.config.ts: Vitest trae su propio Vite y sus
// tipos chocan con los de Vite 8 del proyecto si se mezclan en el mismo fichero.
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
