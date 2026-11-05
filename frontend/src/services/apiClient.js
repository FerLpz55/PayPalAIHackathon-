import { mockApi, resetDemoData as mockResetDemoData } from './mockApi.js'

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
export const isConnectedMode = Boolean(API_BASE_URL)

const SESSION_KEY = 'tallerclaro.session.v1'

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
    status: order.status || 'pending',
    date: order.created_at ? order.created_at.slice(0, 10) : (order.date || new Date().toISOString().slice(0, 10)),
    paid: Number(order.paid_amount ?? order.paid ?? 0),
    spent: Number(order.spent ?? 0),
    receipts: Array.isArray(order.receipts) ? order.receipts : [],
    payments: Array.isArray(order.payments) ? order.payments : [],
  }
}

async function apiRequest(path, options = {}) {
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

export function adaptAccountingSummary(summary = {}) {
  return {
    currency: summary.currency || 'USD',
    ordersCount: Number(summary.orders_count ?? 0),
    awaitingDeposit: Number(summary.orders_awaiting_deposit ?? 0),
    totalContracted: Number(summary.total_contracted ?? 0),
    collectedTotal: Number(summary.collected_total ?? 0),
    pendingToCollect: Number(summary.pending_to_collect ?? 0),
  }
}

export const apiClient = {
  async listOrders() {
    if (!isConnectedMode) {
      return mockApi.listOrders()
    }
    const data = await apiRequest('/api/orders', { isWorkshopRoute: true })
    const list = Array.isArray(data?.orders) ? data.orders : (Array.isArray(data) ? data : [])
    return list.map(adaptOrderResponse)
  },

  async getQuote(quoteId) {
    if (!isConnectedMode) {
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
    if (!isConnectedMode) {
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

    // Request proposal generation
    try {
      await apiRequest(`/api/quotes/${quoteId}/proposal`, {
        method: 'POST',
        isWorkshopRoute: true,
      })
    } catch (proposalErr) {
      // If /proposal is not routed, try /generate
      if (proposalErr.status === 404) {
        try {
          await apiRequest(`/api/quotes/${quoteId}/generate`, {
            method: 'POST',
            isWorkshopRoute: true,
          })
        } catch {
          // Keep quote as draft if proposal generation encounters an issue
        }
      }
    }

    // Retrieve full quote with calculated totals and line items
    const fullQuote = await apiRequest(`/api/quotes/${quoteId}`, {
      customerToken: token,
    })

    return adaptQuoteResponse(fullQuote, { name: customerName, email: customerEmail })
  },

  async submitMissingInfo(quoteId, additionalInfo) {
    if (!isConnectedMode) {
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

    let updatedQuoteData
    try {
      updatedQuoteData = await apiRequest(`/api/quotes/${targetId}/proposal`, {
        method: 'POST',
        isWorkshopRoute: true,
        body,
      })
    } catch (err) {
      if (err.status === 404) {
        updatedQuoteData = await apiRequest(`/api/quotes/${targetId}/generate`, {
          method: 'POST',
          isWorkshopRoute: true,
          body,
        })
      } else {
        throw err
      }
    }

    // Refresh full quote to ensure deposit, balance, and all fields are loaded
    try {
      const fullQuote = await apiRequest(`/api/quotes/${targetId}`)
      return adaptQuoteResponse(fullQuote)
    } catch {
      return adaptQuoteResponse(updatedQuoteData)
    }
  },

  async approveQuote(quoteId) {
    if (!isConnectedMode) {
      return mockApi.approveQuote()
    }

    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    const orderData = await apiRequest(`/api/quotes/${targetId}/approve`, {
      method: 'POST',
    })

    if (orderData?.id) {
      saveSession({ activeOrderId: parseNumericId(orderData.id) })
    }

    // Fetch the updated quote so the UI shows approved state
    const updatedQuote = await apiRequest(`/api/quotes/${targetId}`)
    return adaptQuoteResponse(updatedQuote)
  },

  async rejectQuote(quoteId) {
    if (!isConnectedMode) {
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
    if (!isConnectedMode) {
      const orders = await mockApi.listOrders()
      const found = orders.find((o) => o.id === orderId || o.orderId === parseNumericId(orderId))
      return found || null
    }

    const targetId = parseNumericId(orderId)
    const data = await apiRequest(`/api/orders/${targetId}`, { isWorkshopRoute: true })
    return adaptOrderResponse(data)
  },

  async updateOrderStatus(orderId, status) {
    if (!isConnectedMode) {
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
    if (!isConnectedMode) {
      const kind = typeof orderIdOrKind === 'string' && (orderIdOrKind === 'deposit' || orderIdOrKind === 'balance')
        ? orderIdOrKind
        : (type || 'deposit')
      return mockApi.simulatePayment(kind)
    }

    // In connected mode, simulate demo payment behavior client-side
    const kind = typeof orderIdOrKind === 'string' && (orderIdOrKind === 'deposit' || orderIdOrKind === 'balance')
      ? orderIdOrKind
      : (type || 'deposit')
    return mockApi.simulatePayment(kind)
  },

  async recordDemoCompletionNote(orderId) {
    return mockApi.recordDemoCompletionNote(orderId)
  },

  async askAccountingAssistant(question) {
    if (!isConnectedMode) {
      return mockApi.askAccountingAssistant(question)
    }
    const data = await apiRequest('/api/accounting/assistant', {
      method: 'POST',
      isWorkshopRoute: true,
      body: JSON.stringify({ question }),
    })
    return {
      question: data?.question ?? question,
      answer: data?.answer ?? '',
      summary: adaptAccountingSummary(data?.summary),
      isDemo: false,
    }
  },

  async addReceipt(orderId, file) {
    return mockApi.addReceipt(orderId, file)
  },

  resetDemoData() {
    mockResetDemoData()
    clearSession()
  },
}
