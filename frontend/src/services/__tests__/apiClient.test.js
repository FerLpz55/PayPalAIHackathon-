import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../apiClient.js'
import { getSession, saveSession, saveWorkshopSession } from '../sessionStore.js'

function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function requestAt(index) {
  return globalThis.fetch.mock.calls[index]
}

describe('apiClient workshop session', () => {
  let store

  beforeEach(() => {
    store = {}
    globalThis.sessionStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value) },
      removeItem: (key) => { delete store[key] },
      clear: () => { store = {} },
    }
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('logs in with JSON credentials and stores only the non-secret session metadata', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse(200, {
      authenticated: true,
      carpenter_id: 1,
      username: 'taller',
      csrf_token: 'csrf-abc',
      idle_timeout_seconds: 1800,
      absolute_timeout_seconds: 28800,
    }))

    const session = await apiClient.loginWorkshop('taller', 'secret-pass')

    expect(session).toMatchObject({ authenticated: true, username: 'taller', carpenterId: 1, csrfToken: 'csrf-abc' })
    expect(getSession().workshopSession.csrfToken).toBe('csrf-abc')
    expect(JSON.stringify(getSession())).not.toContain('secret-pass')

    const [url, options] = requestAt(0)
    expect(url).toBe('http://127.0.0.1:8000/api/auth/login')
    expect(options.credentials).toBe('include')
    expect(options.headers.Authorization).toBeUndefined()
    expect(JSON.parse(options.body)).toEqual({ username: 'taller', password: 'secret-pass' })
  })

  it('returns null and clears the stored session when the backend rejects the cookie', async () => {
    saveWorkshopSession({ authenticated: true, csrfToken: 'old' })
    globalThis.fetch.mockResolvedValue(jsonResponse(401, { detail: 'Workshop session required' }))

    await expect(apiClient.getWorkshopSession()).resolves.toBeNull()

    expect(getSession().workshopSession).toBeNull()
  })

  it('sends cookies and never a Basic Authorization header on workshop list requests', async () => {
    saveSession({ customerToken: 'stale-customer-token' })
    saveWorkshopSession({ authenticated: true, csrfToken: 'csrf-abc' })
    globalThis.fetch.mockResolvedValue(jsonResponse(200, { orders: [] }))

    await apiClient.listOrders()

    const [, options] = requestAt(0)
    expect(options.credentials).toBe('include')
    expect(options.headers.Authorization).toBeUndefined()
    expect(options.headers['X-Customer-Token']).toBeUndefined()
  })

  it('logs out with the CSRF header and clears local session metadata', async () => {
    saveWorkshopSession({ authenticated: true, csrfToken: 'csrf-abc' })
    globalThis.fetch.mockResolvedValue(new Response(null, { status: 204 }))

    await apiClient.logoutWorkshop()

    const [url, options] = requestAt(0)
    expect(url).toBe('http://127.0.0.1:8000/api/auth/logout')
    expect(options.method).toBe('POST')
    expect(options.headers['X-CSRF-Token']).toBe('csrf-abc')
    expect(getSession().workshopSession).toBeNull()
  })
})

describe('apiClient quote generation', () => {
  beforeEach(() => {
    const store = {}
    globalThis.sessionStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value) },
      removeItem: (key) => { delete store[key] },
      clear: () => { Object.keys(store).forEach((key) => delete store[key]) },
    }
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('generates the proposal as the customer owner, not as the workshop', async () => {
    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(201, { id: 5, customer_token: 'cust-5' }))
      .mockResolvedValueOnce(jsonResponse(200, { id: '5', status: 'ready' }))
      .mockResolvedValueOnce(jsonResponse(200, {
        id: 5,
        status: 'ready',
        total: 1000,
        deposit_amount: 500,
        balance_amount: 500,
        items: [],
      }))

    const quote = await apiClient.createQuote({
      customer: 'Ana',
      email: 'ana@example.com',
      description: 'A solid oak table 1.80m long',
    })

    expect(quote.total).toBe(1000)
    const [, generateOptions] = requestAt(1)
    expect(generateOptions.headers['X-Customer-Token']).toBe('cust-5')
    expect(generateOptions.headers.Authorization).toBeUndefined()
    expect(getSession().customerToken).toBe('cust-5')
  })

  it('propagates an AI failure instead of leaving a silent draft', async () => {
    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(201, { id: 5, customer_token: 'cust-5' }))
      .mockResolvedValueOnce(jsonResponse(503, {
        code: 'SERVICE_UNAVAILABLE',
        message: 'AI service is not configured',
      }))

    await expect(apiClient.createQuote({
      customer: 'Ana',
      email: 'ana@example.com',
      description: 'A solid oak table 1.80m long',
    })).rejects.toThrow(/saved, but the estimate could not be generated: AI service is not configured/)

    expect(globalThis.fetch).toHaveBeenCalledTimes(2)
    expect(getSession().customerToken).toBe('cust-5')
  })
})

describe('apiClient payment reconciliation', () => {
  beforeEach(() => {
    const store = {}
    globalThis.sessionStorage = {
      getItem: (key) => (Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null),
      setItem: (key, value) => { store[key] = String(value) },
      removeItem: (key) => { delete store[key] },
      clear: () => { Object.keys(store).forEach((key) => delete store[key]) },
    }
    saveSession({ customerToken: 'cust-1' })
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reconciles through POST /sync and never calls the legacy capture route', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse(200, {
      id: '9',
      order_id: '4',
      status: 'completed',
      paypal_order_id: 'PP-9',
    }))

    const payment = await apiClient.syncPayment('9')

    expect(payment.status).toBe('completed')
    expect(requestAt(0)[0]).toBe('http://127.0.0.1:8000/api/payments/9/sync')
    expect(requestAt(0)[1].method).toBe('POST')
    expect(globalThis.fetch.mock.calls.some(([url]) => String(url).includes('/capture'))).toBe(false)
  })

  it('rejects an unrecognized payment state instead of showing success', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse(200, { id: '9', status: 'mystery' }))

    await expect(apiClient.syncPayment(9)).rejects.toThrow(/unrecognized payment state/)
  })

  it('cancels a pending attempt only when the backend confirms cancellation', async () => {
    globalThis.fetch.mockResolvedValueOnce(jsonResponse(200, { id: '9', status: 'cancelled' }))
    await expect(apiClient.cancelPayment(9)).resolves.toMatchObject({ status: 'cancelled' })

    globalThis.fetch.mockResolvedValueOnce(jsonResponse(200, { id: '9', status: 'pending' }))
    await expect(apiClient.cancelPayment(9)).rejects.toThrow(/did not confirm the payment attempt as cancelled/)
  })
})
