/**
 * Adaptadores de datos de la API hacia modelos de dominio en UI.
 */

import { getSession } from './sessionStore.js'

const codeToNumericId = new Map()

function numberOrNull(value) {
  if (value == null || typeof value === 'string' && value.trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function parseNumericId(id) {
  if (id == null) return null
  if (typeof id === 'number') return id
  if (typeof id === 'object') {
    return parseNumericId(id.orderId ?? id.numericId ?? id.id)
  }
  const str = String(id).trim()
  if (codeToNumericId.has(str)) {
    return codeToNumericId.get(str)
  }
  const digits = str.replace(/\D/g, '')
  return digits ? parseInt(digits, 10) : id
}

/** Código corto compartido por cotización y pedido: TC-(1000 + id de cotización). */
export function shortCodeForQuote(quoteId) {
  const numeric = Number(quoteId)
  return Number.isInteger(numeric) && numeric > 0 ? `TC-${1000 + numeric}` : null
}

function displayOrderCode(order) {
  const code = typeof order.code === 'string' ? order.code.trim() : ''
  // Pedidos antiguos guardaron un UUID (TC-<32 hex>); se muestran con el código corto.
  if (code && !/^TC-[0-9a-f]{32}$/i.test(code)) return code
  return shortCodeForQuote(parseNumericId(order.quote_id))
    || (order.id ? (String(order.id).startsWith('TC-') ? String(order.id) : `TC-${order.id}`) : 'TC-Order')
}

/** Medidas detectadas como texto legible; vacío si no se detectó ninguna. */
export function formatMeasurements(measurements) {
  if (!measurements) return ''
  return [
    measurements.width && `${measurements.width} wide`,
    measurements.height && `${measurements.height} tall`,
    measurements.depth && `${measurements.depth} deep`,
  ].filter(Boolean).join(' · ')
}

export function extractMeasurements(text) {
  if (!text) return { width: null, height: null, depth: null, unit: 'm' }
  const widthMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:(?:de\s*)?anch[oa]|wide)\b/i)
  const heightMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:(?:de\s*)?alt[oa]|tall|high)\b/i)
  const depthMatch = text.match(/(\d+(?:[.,]\d+)?\s*(?:m|cm|mm))\s*(?:(?:de\s*)?profund[a-z]*|deep)\b/i)

  return {
    width: widthMatch?.[1] || null,
    height: heightMatch?.[1] || null,
    depth: depthMatch?.[1] || null,
    unit: 'm',
  }
}

export function adaptQuoteResponse(data, fallbackCustomer = {}) {
  if (!data) return null
  const session = getSession()
  const customerName = fallbackCustomer.name || fallbackCustomer.customer || session.customerName || data.customer_name || 'Cliente'
  const customerEmail = fallbackCustomer.email || session.customerEmail || data.customer_email || ''

  const total = numberOrNull(data.total)
  const deposit = numberOrNull(data.deposit_amount)
  const balance = numberOrNull(data.balance_amount)

  const items = Array.isArray(data.items)
    ? data.items.map((item, index) => ({
        id: item.id || `item-${index}`,
        label: item.description || item.label || 'Item',
        kind: (item.type || item.kind || 'material').toLowerCase(),
        amount: numberOrNull(item.amount),
        quantity: numberOrNull(item.quantity),
        unitAmount: numberOrNull(item.unit_amount ?? item.unitAmount),
        unit: item.unit || null,
      }))
    : []

  const measurements = data.measurements || extractMeasurements(data.request || data.description)

  const suggestedProducts = Array.isArray(data.suggested_products || data.suggestedProducts)
    ? (data.suggested_products || data.suggestedProducts).map((prod, idx) => ({
        id: prod.id || `sugg-${idx}`,
        title: prod.title || 'Material verificado',
        priceUsd: numberOrNull(prod.price_usd ?? prod.priceUsd),
        source: prod.source || 'Store',
        url: prod.url || null,
        imageUrl: prod.image_url || prod.imageUrl || null,
      }))
    : []

  return {
    id: data.code || shortCodeForQuote(parseNumericId(data.id)) || (data.id ? String(data.id) : 'TC-New'),
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
    suggestedProducts,
    customer_token: data.customer_token || session.customerToken || null,
    createdAt: data.created_at || new Date().toISOString(),
    isDemo: false,
  }
}

export function adaptOrderResponse(order) {
  if (!order) return null
  const totalValue = order.total ?? order.amount
  const total = numberOrNull(totalValue)
  const depositValue = order.deposit_amount ?? order.deposit
  const balanceValue = order.balance_amount ?? order.balance
  const deposit = numberOrNull(depositValue)
  const balance = numberOrNull(balanceValue)
  const numericOrderId = parseNumericId(order.id)
  const resolvedId = displayOrderCode(order)
  if (numericOrderId != null && resolvedId) {
    codeToNumericId.set(String(resolvedId), numericOrderId)
  }

  return {
    id: resolvedId,
    orderId: numericOrderId,
    quoteId: parseNumericId(order.quote_id),
    customer: order.customer_name || order.customer || 'Cliente',
    email: order.customer_email || order.email || '',
    project: order.project_request || order.project || 'Proyecto de carpintería',
    amount: total,
    deposit,
    balance,
    remainingBalance: numberOrNull(order.remaining_balance),
    status: order.status || 'pending',
    date: order.created_at ? order.created_at.slice(0, 10) : (order.date || new Date().toISOString().slice(0, 10)),
    paid: numberOrNull(order.paid_amount ?? order.paid),
    spent: numberOrNull(order.spent),
    receipts: Array.isArray(order.receipts) ? order.receipts : [],
    payments: Array.isArray(order.payments) ? order.payments : [],
  }
}

export function getRemainingBalance(order) {
  if (!order) return null
  if (order.remainingBalance != null) {
    const remaining = numberOrNull(order.remainingBalance)
    return remaining == null ? null : Math.max(remaining, 0)
  }
  if (order.amount == null || order.paid == null) return null
  const amount = numberOrNull(order.amount)
  const paid = numberOrNull(order.paid)
  return amount == null || paid == null ? null : Math.max(amount - paid, 0)
}

export function adaptAccountingSummary(summary = {}) {
  const firstNumber = (...values) => {
    const value = values.find((candidate) => candidate != null)
    return numberOrNull(value)
  }
  return {
    currency: summary.currency || 'USD',
    ordersCount: firstNumber(summary.orders_count, summary.ordersCount),
    activeOrdersCount: firstNumber(summary.active_orders_count, summary.activeOrdersCount),
    deliveredOrdersCount: firstNumber(summary.delivered_orders_count, summary.deliveredOrdersCount),
    awaitingDeposit: firstNumber(summary.orders_awaiting_deposit, summary.awaitingDeposit),
    ordersWithBalanceDue: firstNumber(summary.orders_with_balance_due, summary.ordersWithBalanceDue),
    totalContracted: firstNumber(summary.total_contracted, summary.totalContracted),
    collectedTotal: firstNumber(summary.collected_total, summary.collectedTotal),
    collectedDeposits: firstNumber(summary.collected_deposits, summary.collectedDeposits),
    collectedBalances: firstNumber(summary.collected_balances, summary.collectedBalances),
    pendingToCollect: firstNumber(summary.pending_to_collect, summary.pendingToCollect),
    averageOrderValue: firstNumber(summary.average_order_value, summary.averageOrderValue),
  }
}
