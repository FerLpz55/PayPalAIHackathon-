import { mockApi, resetDemoData as mockResetDemoData } from './mockApi.js'
import {
  API_BASE_URL,
  isDemoMode,
  isConnectedMode,
  isConfigurationMissing,
  apiRequest,
} from './http.js'
import {
  adaptQuoteResponse,
  adaptOrderResponse,
  adaptAccountingSummary,
  parseNumericId,
} from './adapters.js'
import {
  getSession,
  saveSession,
  clearSession,
  getWorkshopSession,
  saveWorkshopSession,
  readPendingPayment,
  savePendingPayment,
  getPendingPayment,
  getAnyPendingPayment,
  getCompletedPayment,
  clearPendingPayment,
  discardPendingPayment,
  clearUnresolvedPaymentAttempt,
} from './sessionStore.js'
import { isSafePayPalUrl } from '../utils/security.js'

export {
  API_BASE_URL,
  isDemoMode,
  isConnectedMode,
  isConfigurationMissing,
  getSession,
  saveSession,
  clearSession,
  getWorkshopSession,
  adaptQuoteResponse,
  adaptOrderResponse,
}

const PAYMENT_STATUSES = new Set(['pending', 'completed', 'failed', 'cancelled'])

function normalizePaymentStatus(value) {
  return String(value || '').trim().toLowerCase()
}

function toWorkshopSession(data) {
  return {
    authenticated: true,
    username: data.username || null,
    carpenterId: data.carpenter_id ?? null,
    csrfToken: data.csrf_token || null,
    idleTimeoutSeconds: data.idle_timeout_seconds ?? null,
    absoluteTimeoutSeconds: data.absolute_timeout_seconds ?? null,
  }
}

function customerRequestOptions() {
  const session = getSession()
  return session.customerToken
    ? { customerToken: session.customerToken }
    : { workshopSession: true }
}

export const apiClient = {
  // --- Sesión del taller (cookie HttpOnly + CSRF) ---

  async loginWorkshop(username, password) {
    if (isDemoMode) {
      return { authenticated: true, username: 'demo', carpenterId: 1, demo: true }
    }
    const data = await apiRequest('/api/auth/login', {
      method: 'POST',
      omitCustomerToken: true,
      body: JSON.stringify({ username, password }),
    })
    const workshopSession = toWorkshopSession(data)
    saveWorkshopSession(workshopSession)
    return workshopSession
  },

  async getWorkshopSession() {
    if (isDemoMode) {
      return { authenticated: true, username: 'demo', carpenterId: 1, demo: true }
    }
    try {
      const data = await apiRequest('/api/auth/session', { omitCustomerToken: true })
      const workshopSession = toWorkshopSession(data)
      saveWorkshopSession(workshopSession)
      return workshopSession
    } catch (error) {
      if (error?.status === 401) {
        saveWorkshopSession(null)
        return null
      }
      throw error
    }
  },

  async logoutWorkshop() {
    if (isDemoMode) {
      clearSession()
      return
    }
    try {
      await apiRequest('/api/auth/logout', {
        method: 'POST',
        workshopSession: true,
        omitCustomerToken: true,
      })
    } finally {
      saveWorkshopSession(null)
    }
  },

  // --- Pedidos y cotizaciones ---

  async listOrders() {
    if (isDemoMode) {
      return mockApi.listOrders()
    }
    const data = await apiRequest('/api/orders', { workshopSession: true })
    const list = Array.isArray(data?.orders) ? data.orders : (Array.isArray(data) ? data : [])
    return list.map(adaptOrderResponse).filter((order) => order && order.status !== 'deleted')
  },

  async getQuote(quoteId, options = {}) {
    if (isDemoMode) {
      return mockApi.getQuote(quoteId)
    }
    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    if (!targetId) return null

    try {
      const queryParam = options?.query ? `?q=${encodeURIComponent(options.query)}` : ''
      const token = options?.customerToken || session.customerToken
      const data = await apiRequest(`/api/quotes/${targetId}${queryParam}`, {
        ...(token ? { customerToken: token } : { workshopSession: true }),
      })
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
      omitCustomerToken: true,
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

    // El cliente propietario puede generar su propuesta; ya no se usa la ruta
    // de taller. Un fallo del proveedor se propaga con el enlace ya guardado,
    // en lugar de dejar una cotización vacía como si estuviera lista.
    try {
      await apiRequest(`/api/quotes/${quoteId}/generate`, {
        method: 'POST',
        customerToken: token,
      })
    } catch (error) {
      const wrapped = new Error(
        error?.message
          ? `Your request was saved, but the estimate could not be generated: ${error.message}`
          : 'Your request was saved, but the estimate could not be generated. Reopen your quote to retry.'
      )
      wrapped.status = error?.status
      wrapped.cause = error
      throw wrapped
    }

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

    await apiRequest(`/api/quotes/${targetId}/generate`, {
      method: 'POST',
      ...customerRequestOptions(),
      body,
    })

    // Refresca la cotización completa para cargar anticipo, saldo y demás campos.
    const fullQuote = await apiRequest(`/api/quotes/${targetId}`, customerRequestOptions())
    return adaptQuoteResponse(fullQuote)
  },

  async approveQuote(quoteId) {
    if (isDemoMode) {
      return mockApi.approveQuote()
    }

    const session = getSession()
    const targetId = parseNumericId(quoteId || session.activeQuoteId)
    const orderData = await apiRequest(`/api/quotes/${targetId}/approve`, {
      method: 'POST',
      ...customerRequestOptions(),
    })

    if (orderData?.id) {
      saveSession({ activeOrderId: parseNumericId(orderData.id), activeOrderQuoteId: targetId })
    }

    // Refresca la cotización para reflejar el estado aprobado en la UI.
    const updatedQuote = await apiRequest(`/api/quotes/${targetId}`, customerRequestOptions())
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
      ...customerRequestOptions(),
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
    const data = await apiRequest(`/api/orders/${targetId}`, customerRequestOptions())
    return adaptOrderResponse(data)
  },

  async getCustomerContext() {
    if (!isConnectedMode) return null
    const token = getSession().customerToken
    if (!token) return null
    let data
    try {
      data = await apiRequest('/api/customer/context', { customerToken: token })
    } catch (error) {
      // Solo se descarta el enlace de cliente; una sesión de taller en la misma
      // pestaña no debe cerrarse por un token de cliente inválido.
      if (error?.status === 401) saveSession({ customerToken: null })
      throw error
    }
    const quote = adaptQuoteResponse(data?.quote)
    const order = data?.order ? adaptOrderResponse(data.order) : null
    if (quote?.numericId) {
      saveSession({
        activeQuoteId: quote.numericId,
        customerName: quote.customer,
        customerEmail: quote.email,
      })
    }
    if (order) {
      saveSession({
        activeOrderId: order.orderId,
        activeOrderQuoteId: quote?.numericId ?? order.quoteId,
      })
    }
    return {
      quote,
      order,
      payments: Array.isArray(data?.payments) ? data.payments : [],
    }
  },

  async getCustomerOrder(quoteId) {
    if (!isConnectedMode) return null
    const session = getSession()
    if (!session.customerToken || !session.activeOrderId || String(session.activeOrderQuoteId) !== String(parseNumericId(quoteId))) return null
    return this.getOrder(session.activeOrderId)
  },

  // --- Recuperación de pagos en el navegador ---

  getPendingPayment(orderId, type) {
    return getPendingPayment(parseNumericId(orderId), type)
  },

  getAnyPendingPayment() {
    return getAnyPendingPayment()
  },

  getCompletedPayment(orderId, type) {
    return getCompletedPayment(parseNumericId(orderId), type)
  },

  clearPendingPayment(paymentId) {
    clearPendingPayment(parseNumericId(paymentId))
  },

  discardPendingPayment(paymentId) {
    discardPendingPayment(parseNumericId(paymentId))
  },

  clearUnresolvedPaymentAttempt(orderId, type) {
    clearUnresolvedPaymentAttempt(parseNumericId(orderId), type)
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
    const rawApprovalUrl = typeof data?.approval_url === 'string' ? data.approval_url : ''

    if (!paymentId || !paypalOrderId) {
      throw new Error('The backend response did not include payment identifiers. This attempt cannot safely be repeated yet.')
    }

    const safeApprovalUrl = isSafePayPalUrl(rawApprovalUrl) ? rawApprovalUrl : null

    const payment = {
      paymentId,
      paypalOrderId,
      orderId: targetOrderId,
      type,
      amount: data.amount,
      currency: data.currency,
      approvalUrl: safeApprovalUrl,
      unresolved: false,
      checkoutIssue: rawApprovalUrl && !safeApprovalUrl ? 'The backend returned an unsafe PayPal approval URL.' : null,
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

  async syncPayment(paymentId) {
    if (isDemoMode) throw new Error('Payment reconciliation is unavailable in DEMO mode.')
    if (isConfigurationMissing) throw new Error('Backend connection is not configured. Payment status cannot be verified.')
    const payment = await apiRequest(`/api/payments/${parseNumericId(paymentId)}/sync`, {
      method: 'POST',
    })
    const status = normalizePaymentStatus(payment?.status)
    if (!PAYMENT_STATUSES.has(status)) {
      throw new Error('The backend returned an unrecognized payment state. No success is being shown.')
    }
    return payment
  },

  async cancelPayment(paymentId) {
    if (isDemoMode) throw new Error('Payment cancellation is unavailable in DEMO mode.')
    if (isConfigurationMissing) throw new Error('Backend connection is not configured. Payment status cannot be changed.')
    const payment = await apiRequest(`/api/payments/${parseNumericId(paymentId)}/cancel`, {
      method: 'POST',
    })
    if (normalizePaymentStatus(payment?.status) !== 'cancelled') {
      throw new Error('The backend did not confirm the payment attempt as cancelled.')
    }
    return payment
  },

  // --- Taller ---

  async updateOrderStatus(orderId, status) {
    if (isDemoMode) {
      return mockApi.updateStatus(orderId, status)
    }

    const targetId = parseNumericId(orderId)
    const data = await apiRequest(`/api/orders/${targetId}`, {
      method: 'PATCH',
      workshopSession: true,
      body: JSON.stringify({ status }),
    })
    return adaptOrderResponse(data)
  },

  async updateStatus(orderId, status) {
    return this.updateOrderStatus(orderId, status)
  },

  async cancelOrder(orderId) {
    return this.updateOrderStatus(orderId, 'cancelled')
  },

  async deleteOrder(orderId) {
    if (isDemoMode) {
      return mockApi.deleteOrder(orderId)
    }

    const targetId = parseNumericId(orderId)
    const data = await apiRequest(`/api/orders/${targetId}`, {
      method: 'PATCH',
      workshopSession: true,
      body: JSON.stringify({ status: 'deleted' }),
    })
    return adaptOrderResponse(data)
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

  async reissueCustomerAccess(quoteId) {
    if (isDemoMode) throw new Error('Customer access links are unavailable in DEMO mode.')
    const targetId = parseNumericId(quoteId)
    const data = await apiRequest(`/api/quotes/${targetId}/customer-access`, {
      method: 'POST',
      workshopSession: true,
    })
    if (!data?.customer_token) {
      throw new Error('The backend did not return a customer token.')
    }
    return { quoteId: parseNumericId(data.quote_id), customerToken: data.customer_token }
  },

  async getFinancialSummary() {
    if (isDemoMode) {
      const orders = await mockApi.listOrders()
      const collected = orders.reduce((sum, order) => sum + Number(order.paid || 0), 0)
      const contracted = orders.reduce((sum, order) => sum + Number(order.amount || 0), 0)
      const pending = orders
        .filter((order) => order.status !== 'delivered')
        .reduce((sum, order) => sum + Math.max(0, Number(order.amount || 0) - Number(order.paid || 0)), 0)
      const awaitingDeposit = orders.filter((order) => !Number(order.paid)).length
      return {
        currency: 'USD',
        ordersCount: orders.length,
        activeOrdersCount: orders.length,
        deliveredOrdersCount: orders.filter((order) => order.status === 'delivered').length,
        awaitingDeposit,
        ordersWithBalanceDue: orders.filter((order) => Number(order.paid) > 0 && Math.max(0, Number(order.amount || 0) - Number(order.paid || 0)) > 0).length,
        totalContracted: contracted,
        collectedTotal: collected,
        collectedDeposits: collected,
        collectedBalances: 0,
        pendingToCollect: pending,
        averageOrderValue: orders.length ? contracted / orders.length : 0,
      }
    }
    const data = await apiRequest('/api/accounting/summary', { workshopSession: true })
    return adaptAccountingSummary(data)
  },

  async askAccountingAssistant(question) {
    if (isDemoMode) {
      return mockApi.askAccountingAssistant(question)
    }
    const data = await apiRequest('/api/accounting/assistant', {
      method: 'POST',
      workshopSession: true,
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
    if (!isDemoMode) throw new Error('Demo data is available only when VITE_APP_MODE=demo is explicitly selected.')
    return mockApi.addReceipt(orderId, file)
  },

  resetDemoData() {
    if (!isDemoMode) throw new Error('Demo data can be reset only when VITE_APP_MODE=demo is explicitly selected.')
    mockResetDemoData()
    clearSession()
  },
}
