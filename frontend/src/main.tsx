import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import './index.css'
import App from './App'
import { ApiError } from './api/client'
import { AuthProvider } from './auth'
import { ToastHost, notify } from './components/Toast'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  // Cualquier acción que falle avisa al anfitrión (feedback uniforme).
  mutationCache: new MutationCache({
    onError: (error) => {
      const msg = error instanceof ApiError ? error.message : 'Algo no ha ido bien. Inténtalo de nuevo.'
      notify(msg, 'error')
    },
  }),
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <App />
          <ToastHost />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
