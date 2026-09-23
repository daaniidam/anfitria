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

/**
 * Cliente HTTP. La sesión viaja en una cookie httpOnly (no accesible por JS →
 * resiste XSS), por eso siempre enviamos `credentials: 'include'` y no guardamos
 * el token en localStorage.
 */
export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }

  const response = await fetch(`${BASE}${path}`, {
    method: options.method ?? 'GET',
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
