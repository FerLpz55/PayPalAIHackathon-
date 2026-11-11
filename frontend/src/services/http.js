/**
 * Capa de transporte HTTP y manejo de errores para TallerClaro.
 *
 * La autenticación del taller usa una cookie de sesión `HttpOnly` emitida por
 * el backend. Las cookies viajan con `credentials: "include"`; el token CSRF
 * viaja en `X-CSRF-Token` y se guarda en `sessionStorage` porque el frontend
 * puede vivir en otro origen y no puede leer la cookie CSRF del backend.
 */

import { getSession } from './sessionStore.js'

export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const isDemoMode = String(import.meta.env?.VITE_APP_MODE || '').trim().toLowerCase() === 'demo'
export const isConnectedMode = !isDemoMode && Boolean(API_BASE_URL)
export const isConfigurationMissing = !isDemoMode && !API_BASE_URL

export function isSecureWorkshopTransport() {
  if (!API_BASE_URL) return false
  try {
    const { protocol, hostname } = new URL(API_BASE_URL)
    return protocol === 'https:' || (protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(hostname))
  } catch {
    return false
  }
}

/** Evento emitido cuando el backend rechaza la sesión del taller. */
export const SESSION_EXPIRED_EVENT = 'tallerclaro:session-expired'
export const CSRF_HEADER = 'X-CSRF-Token'

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export class ApiError extends Error {
  constructor(message, status, payload = null, headers = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
    this.code = payload?.code || payload?.detail?.code || null
    this.retryAfter = headers?.get?.('retry-after') || payload?.retry_after || null
  }
}

function readCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) return null
  const prefix = `${name}=`
  const match = document.cookie.split('; ').find((row) => row.startsWith(prefix))
  return match ? decodeURIComponent(match.slice(prefix.length)) : null
}

function csrfToken(session) {
  return (
    session?.workshopSession?.csrfToken ||
    readCookie('__Host-tallerclaro_csrf') ||
    null
  )
}

function notifySessionExpired() {
  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') return
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT))
}

export async function apiRequest(path, options = {}) {
  if (!isConnectedMode) {
    throw new ApiError(
      'Backend connection is not configured. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo for sample data.',
      0
    )
  }

  const {
    customerToken,
    workshopSession = false,
    omitCustomerToken = false,
    headers: extraHeaders,
    ...fetchOptions
  } = options

  const session = getSession()
  const sendsWorkshopCredentials = workshopSession || path === '/api/auth/login'
  if (sendsWorkshopCredentials && !isSecureWorkshopTransport()) {
    throw new ApiError('Workshop credentials require HTTPS. HTTP is allowed only for a loopback development backend.', 0)
  }
  const headers = {
    'Content-Type': 'application/json',
    ...extraHeaders,
  }

  // En rutas de taller se evita reenviar un token de cliente antiguo: el
  // backend da prioridad al token y podría limitar la petición a esa
  // cotización en lugar de usar la sesión del taller.
  if (!omitCustomerToken && !workshopSession) {
    const token = customerToken || session.customerToken
    if (token && !headers['X-Customer-Token']) {
      headers['X-Customer-Token'] = token
    }
  }

  const method = String(fetchOptions.method || 'GET').toUpperCase()
  if (workshopSession && UNSAFE_METHODS.has(method)) {
    const token = csrfToken(session)
    if (token) headers[CSRF_HEADER] = token
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE_URL}${cleanPath}`
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    credentials: 'include',
  })

  if (!response.ok) {
    let errorDetail = null
    try {
      errorDetail = await response.json()
    } catch {
      // Respuesta sin cuerpo JSON
    }

    const message =
      errorDetail?.message ||
      errorDetail?.detail ||
      (Array.isArray(errorDetail?.field_errors)
        ? errorDetail.field_errors.map((e) => `${e.field}: ${e.message}`).join(', ')
        : null) ||
      `HTTP error ${response.status}: ${response.statusText}`

    // Una sesión inválida debe devolver al taller al formulario de acceso; un
    // token de cliente inválido nunca debe cerrar la sesión del taller.
    if (workshopSession && response.status === 401) {
      notifySessionExpired()
    }

    throw new ApiError(message, response.status, errorDetail, response.headers)
  }

  if (response.status === 204) return null
  return response.json()
}
