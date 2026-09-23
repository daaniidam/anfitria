const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

interface Options {
  method?: string
  body?: unknown
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

/**
 * Cliente HTTP. La sesión viaja en una cookie httpOnly (no accesible por JS →
 * resiste XSS), por eso siempre enviamos `credentials: 'include'` y no guardamos
 * el token en localStorage. En las mutaciones reenviamos el token CSRF (double-submit).
 */
export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (method !== 'GET') {
    const csrf = readCookie('csrf_token')
    if (csrf) headers['X-CSRF-Token'] = csrf
  }

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = (await response.json()) as { detail?: string }
      if (typeof data.detail === 'string') detail = data.detail
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Sube un fichero (multipart) con la cookie de sesión y el token CSRF. */
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  const headers: Record<string, string> = {}
  const csrf = readCookie('csrf_token')
  if (csrf) headers['X-CSRF-Token'] = csrf

  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: form,
  })

  if (!response.ok) {
    let detail = response.statusText
    try {
      const data = (await response.json()) as { detail?: string }
      if (typeof data.detail === 'string') detail = data.detail
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(response.status, detail)
  }
  return (await response.json()) as T
}
