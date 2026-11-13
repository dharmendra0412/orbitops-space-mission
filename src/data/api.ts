const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')

/** Build a same-origin API path locally or target a separately hosted API in production. */
export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : '/' + path
  return API_BASE_URL + normalizedPath
}
