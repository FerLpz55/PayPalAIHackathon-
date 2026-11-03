import { mockApi, resetDemoData as mockResetDemoData } from './mockApi.js'

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const isDemoMode = String(import.meta.env?.VITE_APP_MODE || '').trim().toLowerCase() === 'demo'
export const isConnectedMode = !isDemoMode && Boolean(API_BASE_URL)
export const isConfigurationMissing = !isDemoMode && !API_BASE_URL

const SESSION_KEY = 'tallerclaro.session.v1'
const PENDING_PAYMENT_KEY = 'tallerclaro.pending-payment.v1'
const COMPLETED_PAYMENT_KEY = 'tallerclaro.completed-payment.v1'

function readPendingPayment() {
  try {
    const value = JSON.parse(sessionStorage.getItem(PENDING_PAYMENT_KEY) || 'null')
    return value && typeof value === 'object' ? value : null
  } catch {
    return null
  }
}

function savePendingPayment(value) {
  try {
    sessionStorage.setItem(PENDING_PAYMENT_KEY, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    const parsed = raw ? JSON.parse(raw) : {}
    return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {}
  } catch {
    return {}
  }
}

export function saveSession(patch) {
  try {
    const current = getSession()
    const updated = { ...current, ...patch }
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(updated))
    return updated
  } catch {
    return {}
  }
}

export function clearSession() {
  try {
    sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // Ignore storage errors in browser sandbox
  }
}

function parseNumericId(id) {
  if (id == null) return null
  if (typeof id === 'number') return id
  const digits = String(id).replace(/\D/g, '')
  return digits ? parseInt(digits, 10) : id
}

function extractMeasurements(text) {
  if (!text) {
    return { width: '1.20 m', height: '1.80 m', depth: '0.55 m', unit: 'm' }
  }
  const widthMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:de\s*)?anch[oa]/i)
  const heightMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:de\s*)?alt[oa]/i)
  const depthMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:de\s*)?profund[a-z]*/i)

  return {
    width: widthMatch ? widthMatch[1] : '1.20 m',
    height: heightMatch ? heightMatch[1] : '1.80 m',
    depth: depthMatch ? depthMatch[1] : '0.55 m',
    unit: 'm',
  }
}

export function adaptQuoteResponse(data, fallbackCustomer = {}) {
  if (!data) return null
  const session = getSession()
  const customerName = fallbackCustomer.name || fallbackCustomer.customer || session.customerName || data.customer_name || 'Cliente'
  const customerEmail = fallbackCustomer.email || session.customerEmail || data.customer_email || ''

  const total = Number(data.total ?? 0)
  const deposit = Number(data.deposit_amount ?? (total ? Math.round(total * 0.5 * 100) / 100 : 0))
  const balance = Number(data.balance_amount ?? (total ? total - deposit : 0))

  const items = Array.isArray(data.items)
    ? data.items.map((item, index) => ({
        id: item.id || `item-${index}`,
        label: item.description || item.label || 'Item',
        kind: (item.type || item.kind || 'material').toLowerCase(),
        amount: Number(item.amount ?? 0),
        quantity: Number(item.quantity ?? 1),
        unitAmount: Number(item.unit_amount ?? item.unitAmount ?? item.amount ?? 0),
        unit: item.unit || 'unit',
      }))
    : []

  const measurements = data.measurements || extractMeasurements(data.request || data.description)

  return {
    id: data.code || (data.id ? (String(data.id).startsWith('TC-') ? String(data.id) : `TC-${data.id}`) : 'TC-New'),
    numericId: parseNumericId(data.id),
    customer: customerName,
    email: customerEmail,
    project: data.description || data.request || 'Custom woodwork',
    description: data.description || data.request || '',
    request: data.request || data.description || '',
    total,
    deposit,
    balance,
    measurements,
    items,
    status: data.status || 'draft',
    assumptions: Array.isArray(data.assumptions) ? data.assumptions : [],
    missing_info: Array.isArray(data.missing_info) ? data.missing_info : [],
    customer_token: data.customer_token || session.customerToken || null,
    createdAt: data.created_at || new Date().toISOString(),
    isDemo: false,
  }
}

export function adaptOrderResponse(order) {
  if (!order) return null
  const total = Number(order.total ?? order.amount ?? 0)
  const deposit = Number(order.deposit_amount ?? order.deposit ?? (total ? Math.round(total * 0.5 * 100) / 100 : 0))
  const balance = Number(order.balance_amount ?? order.balance ?? (total ? total - deposit : 0))

  return {
    id: order.code || (order.id ? (String(order.id).startsWith('TC-') ? String(order.id) : `TC-${order.id}`) : 'TC-Order'),
    orderId: parseNumericId(order.id),
    quoteId: parseNumericId(order.quote_id),
    customer: order.customer_name || order.customer || 'Cliente',
    email: order.customer_email || order.email || '',
    project: order.project_request || order.project || 'Proyecto de carpintería',
    amount: total,
    deposit,
    balance,
    remainingBalance: order.remaining_balance == null ? null : Number(order.remaining_balance),
    status: order.status || 'pending',
    date: order.created_at ? order.created_at.slice(0, 10) : (order.date || new Date().toISOString().slice(0, 10)),
    paid: Number(order.paid_amount ?? order.paid ?? 0),
    spent: Number(order.spent ?? 0),
    receipts: Array.isArray(order.receipts) ? order.receipts : [],
    payments: Array.isArray(order.payments) ? order.payments : [],
  }
}

async function apiRequest(path, options = {}) {
  if (!isConnectedMode) {
    throw new Error('Backend connection is not configured. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo for sample data.')
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
      // Non-JSON response
    }

    const message =
      errorDetail?.message ||
      errorDetail?.detail ||
      (Array.isArray(errorDetail?.field_errors)
        ? errorDetail.field_errors.map((e) => `${e.field}: ${e.message}`).join(', ')
        : null) ||
      `HTTP error ${response.status}: ${response.statusText}`

    const error = new Error(message)
    error.status = response.status
    error.payload = errorDetail
    throw error
  }

  if (response.status === 204) return null
  return response.json()
}

export const apiClient = {
  async listOrders() {
    if (isDemoMode) {
      return mockApi.listOrders()
    }
    const data = await apiRequest('/api/orders', { isWorkshopRoute: true })
    const list = Array.isArray(data?.orders) ? data.orders : (Array.isArray(data) ? data : [])
    return list.map(adaptOrderResponse)
  },

  async getQuote(quoteId) {
    if (isDemoMode) {
      return mockApi.getQuote(quoteId)
    }
    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    if (!targetId) return null

    try {
      const data = await apiRequest(`/api/quotes/${targetId}`)
      return adaptQuoteResponse(data)
    } catch (err) {
      if (err.status === 404) return null
      throw err
    }
  },

  async createQuote(input) {
    if (isDemoMode) {
      return mockApi.createQuote(input)
    }

    const customerName = (input.customer || input.customerName || '').trim()
    const customerEmail = (input.email || input.customerEmail || '').trim()
    const description = (input.description || input.request || '').trim()

    const createPayload = {
      customer: {
        name: customerName,
        email: customerEmail,
        phone: input.phone || null,
      },
      carpenter_id: 1,
      request: description,
    }

    const created = await apiRequest('/api/quotes', {
      method: 'POST',
      body: JSON.stringify(createPayload),
    })

    const token = created.customer_token
    const quoteId = parseNumericId(created.id)

    saveSession({
      customerToken: token,
      activeQuoteId: quoteId,
      customerName,
      customerEmail,
    })

    // Request proposal generation through the documented route.
    try {
      await apiRequest(`/api/quotes/${quoteId}/generate`, {
        method: 'POST',
        isWorkshopRoute: true,
      })
    } catch {
      // Keep the persisted quote available when generation is unavailable.
    }

    // Retrieve full quote with calculated totals and line items
    const fullQuote = await apiRequest(`/api/quotes/${quoteId}`, {
      customerToken: token,
    })

    return adaptQuoteResponse(fullQuote, { name: customerName, email: customerEmail })
  },

  async submitMissingInfo(quoteId, additionalInfo) {
    if (isDemoMode) {
      const quote = await mockApi.getQuote()
      if (quote) {
        quote.status = 'pending_review'
        quote.missing_info = []
        if (quote.description) {
          quote.description += ` | Additional details: ${additionalInfo}`
        }
        return quote
      }
      return null
    }

    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    const body = JSON.stringify({ additional_info: additionalInfo })

    const updatedQuoteData = await apiRequest(`/api/quotes/${targetId}/generate`, {
      method: 'POST',
      isWorkshopRoute: true,
      body,
    })

    // Refresh full quote to ensure deposit, balance, and all fields are loaded
    try {
      const fullQuote = await apiRequest(`/api/quotes/${targetId}`)
      return adaptQuoteResponse(fullQuote)
    } catch {
      return adaptQuoteResponse(updatedQuoteData)
    }
  },

  async approveQuote(quoteId) {
    if (isDemoMode) {
      return mockApi.approveQuote()
    }

    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    const orderData = await apiRequest(`/api/quotes/${targetId}/approve`, {
      method: 'POST',
    })

    if (orderData?.id) {
      saveSession({ activeOrderId: parseNumericId(orderData.id), activeOrderQuoteId: targetId })
    }

    // Fetch the updated quote so the UI shows approved state
    const updatedQuote = await apiRequest(`/api/quotes/${targetId}`)
    return adaptQuoteResponse(updatedQuote)
  },

  async rejectQuote(quoteId) {
    if (isDemoMode) {
      const quote = await mockApi.getQuote()
      if (quote) {
        quote.status = 'rejected'
        return quote
      }
      return null
    }

    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    const updated = await apiRequest(`/api/quotes/${targetId}/reject`, {
      method: 'POST',
    })
    return adaptQuoteResponse(updated)
  },

  async getOrder(orderId) {
    if (isDemoMode) {
      const orders = await mockApi.listOrders()
      const found = orders.find((o) => o.id === orderId || o.orderId === parseNumericId(orderId))
      return found || null
    }

    const targetId = parseNumericId(orderId)
    const data = await apiRequest(`/api/orders/${targetId}`, { isWorkshopRoute: !getSession().customerToken })
    return adaptOrderResponse(data)
  },

  async getCustomerOrder(quoteId) {
    if (!isConnectedMode) return null
    const session = getSession()
    if (!session.customerToken || !session.activeOrderId || String(session.activeOrderQuoteId) !== String(parseNumericId(quoteId))) return null
    return this.getOrder(session.activeOrderId)
  },

  getPendingPayment(orderId, type) {
    const pending = readPendingPayment()
    return pending && String(pending.orderId) === String(orderId) && pending.type === type ? pending : null
  },

  getAnyPendingPayment() {
    return readPendingPayment()
  },

  getCompletedPayment(orderId, type) {
    try {
      const value = JSON.parse(sessionStorage.getItem(COMPLETED_PAYMENT_KEY) || 'null')
      return value && String(value.orderId) === String(orderId) && value.type === type ? value : null
    } catch {
      return null
    }
  },

  clearPendingPayment(paymentId) {
    const pending = readPendingPayment()
    if (!paymentId || !pending || String(pending.paymentId) !== String(parseNumericId(paymentId))) return
    try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore storage errors */ }
    try { sessionStorage.setItem(COMPLETED_PAYMENT_KEY, JSON.stringify({ orderId: pending.orderId, type: pending.type, paymentId: pending.paymentId })) } catch { /* ignore storage errors */ }
  },

  discardPendingPayment(paymentId) {
    const pending = readPendingPayment()
    if (!paymentId || !pending || String(pending.paymentId) !== String(parseNumericId(paymentId))) return
    try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore storage errors */ }
  },

  clearUnresolvedPaymentAttempt(orderId, type) {
    const pending = readPendingPayment()
    if (pending?.unresolved && String(pending.orderId) === String(parseNumericId(orderId)) && pending.type === type) {
      try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore storage errors */ }
    }
  },

  async createOrderPayment(orderId, type) {
    if (isDemoMode) throw new Error('PayPal checkout is unavailable in DEMO mode.')
    if (isConfigurationMissing) throw new Error('Backend connection is not configured. No payment attempt was created.')
    if (!getSession().customerToken) throw new Error('A customer access token is required to start checkout.')
    if (!['deposit', 'balance'].includes(type)) throw new Error('Unsupported payment type.')
    const targetOrderId = parseNumericId(orderId)
    const existing = readPendingPayment()
    if (existing) {
      throw new Error('A payment attempt is already stored. Verify or reconcile it before starting another.')
    }
    if (!savePendingPayment({ orderId: targetOrderId, type, unresolved: true })) {
      throw new Error('Secure payment recovery storage is unavailable. No payment attempt was started.')
    }
    let data
    try {
      data = await apiRequest(`/api/orders/${targetOrderId}/payments`, {
        method: 'POST',
        body: JSON.stringify({ type }),
      })
    } catch (error) {
      if (error?.status >= 400 && error.status < 500) this.clearUnresolvedPaymentAttempt(targetOrderId, type)
      throw error
    }
    const paymentId = parseNumericId(data?.payment_id)
    const paypalOrderId = data?.paypal_order_id == null ? '' : String(data.paypal_order_id)
    const approvalUrl = typeof data?.approval_url === 'string' ? data.approval_url : ''
    let approvalHost = ''
    try { approvalHost = new URL(approvalUrl).hostname.toLowerCase() } catch { /* invalid URL */ }
    if (!paymentId || !paypalOrderId) throw new Error('The backend response did not include payment identifiers. This attempt cannot safely be repeated yet.')
    const safeApprovalUrl = approvalUrl && approvalUrl.startsWith('https://') && (approvalHost === 'sandbox.paypal.com' || approvalHost.endsWith('.sandbox.paypal.com'))
      ? approvalUrl
      : null
    const payment = {
      paymentId,
      paypalOrderId,
      orderId: parseNumericId(orderId),
      type,
      amount: data.amount,
      currency: data.currency,
      approvalUrl: safeApprovalUrl,
      unresolved: false,
      checkoutIssue: approvalUrl && !safeApprovalUrl ? 'The backend returned an unsafe PayPal approval URL.' : null,
    }
    if (!savePendingPayment(payment)) {
      throw new Error('The backend created a payment, but this browser could not save its recovery details. Do not start another attempt; contact the workshop to reconcile it.')
    }
    return payment
  },

  async getPayment(paymentId) {
    if (!isConnectedMode) return null
    return apiRequest(`/api/payments/${parseNumericId(paymentId)}`)
  },

  async capturePayment(paymentId) {
    if (isDemoMode) throw new Error('Payment capture is unavailable in DEMO mode.')
    if (isConfigurationMissing) throw new Error('Backend connection is not configured. Payment status cannot be verified.')
    const captured = await apiRequest(`/api/payments/${parseNumericId(paymentId)}/capture`, { method: 'POST' })
    if (String(captured?.status || '').toLowerCase() !== 'completed') {
      throw new Error('The server has not confirmed this payment as completed.')
    }
    return captured
  },

  async updateOrderStatus(orderId, status) {
    if (isDemoMode) {
      return mockApi.updateStatus(orderId, status)
    }

    const targetId = parseNumericId(orderId)
    const data = await apiRequest(`/api/orders/${targetId}`, {
      method: 'PATCH',
      isWorkshopRoute: true,
      body: JSON.stringify({ status }),
    })
    return adaptOrderResponse(data)
  },

  async updateStatus(orderId, status) {
    return this.updateOrderStatus(orderId, status)
  },

  async simulatePayment(orderIdOrKind, amount, type) {
    if (isDemoMode) {
      const kind = typeof orderIdOrKind === 'string' && (orderIdOrKind === 'deposit' || orderIdOrKind === 'balance')
        ? orderIdOrKind
        : (type || 'deposit')
      return mockApi.simulatePayment(kind)
    }

    throw new Error('Simulated payments are disabled while connected. Use PayPal checkout.')
  },

  async recordDemoCompletionNote(orderId) {
    if (!isDemoMode) throw new Error('Demo data is available only when VITE_APP_MODE=demo is explicitly selected.')
    return mockApi.recordDemoCompletionNote(orderId)
  },

  async addReceipt(orderId, file) {
    if (!isDemoMode) throw new Error('Demo data is available only when VITE_APP_MODE=demo is explicitly selected.')
    return mockApi.addReceipt(orderId, file)
  },

  resetDemoData() {
    if (!isDemoMode) throw new Error('Demo data can be reset only when VITE_APP_MODE=demo is explicitly selected.')
    mockResetDemoData()
    clearSession()
  },
}
