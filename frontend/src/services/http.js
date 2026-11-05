/**
 * Capa de transporte HTTP y manejo de errores para TallerClaro.
 */

import { getSession } from './sessionStore.js'

export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const isDemoMode = String(import.meta.env?.VITE_APP_MODE || '').trim().toLowerCase() === 'demo'
export const isConnectedMode = !isDemoMode && Boolean(API_BASE_URL)
export const isConfigurationMissing = !isDemoMode && !API_BASE_URL

export class ApiError extends Error {
  constructor(message, status, payload = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export async function apiRequest(path, options = {}) {
  if (!isConnectedMode) {
    throw new ApiError(
      'Backend connection is not configured. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo for sample data.',
      0
    )
  }
  const session = getSession()
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const customerToken = options.customerToken || session.customerToken
  if (customerToken && !headers['X-Customer-Token']) {
    headers['X-Customer-Token'] = customerToken
  }

  if (options.workshopAuth || options.isWorkshopRoute) {
    const creds = session.workshopCredentials || btoa('taller:demo-password')
    if (!headers['Authorization']) {
      headers['Authorization'] = `Basic ${creds}`
    }
  }

  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE_URL}${cleanPath}`
  const response = await fetch(url, { ...options, headers })

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

    throw new ApiError(message, response.status, errorDetail)
  }

  if (response.status === 204) return null
  return response.json()
}
