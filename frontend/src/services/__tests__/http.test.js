import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, SESSION_EXPIRED_EVENT } from '../http.js'
import { saveSession, saveWorkshopSession } from '../sessionStore.js'

function jsonResponse(status, body, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

describe('http transport', () => {
  let store
  let dispatchEvent

  beforeEach(() => {
    store = {}
    globalThis.sessionStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value) },
      removeItem: (key) => { delete store[key] },
      clear: () => { store = {} },
    }
    dispatchEvent = vi.fn()
    globalThis.window = { dispatchEvent }
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete globalThis.window
  })

  it('sends cookies and the customer token on customer requests', async () => {
    saveSession({ customerToken: 'cust-token' })
    globalThis.fetch.mockResolvedValue(jsonResponse(200, { ok: true }))

    const result = await apiRequest('/api/quotes/1', {})

    expect(result).toEqual({ ok: true })
    const [url, options] = globalThis.fetch.mock.calls[0]
    expect(url).toBe('http://127.0.0.1:8000/api/quotes/1')
    expect(options.credentials).toBe('include')
    expect(options.headers['X-Customer-Token']).toBe('cust-token')
    expect(options.headers.Authorization).toBeUndefined()
    expect(options.headers['X-CSRF-Token']).toBeUndefined()
  })

  it('uses the stored CSRF token and omits the customer token on unsafe workshop requests', async () => {
    saveSession({ customerToken: 'cust-token' })
    saveWorkshopSession({ authenticated: true, username: 'taller', csrfToken: 'csrf-123' })
    globalThis.fetch.mockResolvedValue(new Response(null, { status: 204 }))

    const result = await apiRequest('/api/orders/7', {
      method: 'PATCH',
      workshopSession: true,
      body: JSON.stringify({ status: 'in_progress' }),
    })

    expect(result).toBeNull()
    const [, options] = globalThis.fetch.mock.calls[0]
    expect(options.credentials).toBe('include')
    expect(options.headers['X-CSRF-Token']).toBe('csrf-123')
    expect(options.headers['X-Customer-Token']).toBeUndefined()
    expect(options.headers.Authorization).toBeUndefined()
  })

  it('does not send CSRF on safe workshop requests', async () => {
    saveWorkshopSession({ authenticated: true, csrfToken: 'csrf-123' })
    globalThis.fetch.mockResolvedValue(jsonResponse(200, { orders: [] }))

    await apiRequest('/api/orders', { workshopSession: true })

    const [, options] = globalThis.fetch.mock.calls[0]
    expect(options.headers['X-CSRF-Token']).toBeUndefined()
  })

  it('omits the customer token for public auth requests', async () => {
    saveSession({ customerToken: 'cust-token' })
    globalThis.fetch.mockResolvedValue(jsonResponse(200, { authenticated: true }))

    await apiRequest('/api/auth/login', {
      method: 'POST',
      omitCustomerToken: true,
      body: JSON.stringify({ username: 'taller', password: 'x' }),
    })

    const [, options] = globalThis.fetch.mock.calls[0]
    expect(options.headers['X-Customer-Token']).toBeUndefined()
  })

  it('maps backend errors and exposes the status and message', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse(409, { code: 'CONFLICT', message: 'Payment conflict' }))

    await expect(apiRequest('/api/payments/1/sync', { method: 'POST' })).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      code: 'CONFLICT',
      message: 'Payment conflict',
    })
    expect(dispatchEvent).not.toHaveBeenCalled()
  })

  it('emits the session-expired event only when a workshop request gets 401', async () => {
    globalThis.fetch.mockResolvedValueOnce(jsonResponse(401, { detail: 'Workshop session required' }))
    await expect(apiRequest('/api/orders', { workshopSession: true })).rejects.toMatchObject({ status: 401 })

    expect(dispatchEvent).toHaveBeenCalledTimes(1)
    expect(dispatchEvent.mock.calls[0][0].type).toBe(SESSION_EXPIRED_EVENT)

    globalThis.fetch.mockResolvedValueOnce(jsonResponse(401, { detail: 'Invalid customer token' }))
    await expect(apiRequest('/api/orders/1', { customerToken: 'bad' })).rejects.toMatchObject({ status: 401 })
    expect(dispatchEvent).toHaveBeenCalledTimes(1)
  })

  it('reports an unconfigured backend instead of performing a request', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'real')
    vi.stubEnv('VITE_API_BASE_URL', '')
    const fresh = await import('../http.js')

    expect(fresh.isConfigurationMissing).toBe(true)
    await expect(fresh.apiRequest('/api/health')).rejects.toMatchObject({ status: 0 })
    expect(globalThis.fetch).not.toHaveBeenCalled()

    vi.unstubAllEnvs()
    vi.resetModules()
  })
})
