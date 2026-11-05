/**
 * Adaptadores de datos de la API hacia modelos de dominio en UI.
 */

import { getSession } from './sessionStore.js'

export function parseNumericId(id) {
  if (id == null) return null
  if (typeof id === 'number') return id
  const digits = String(id).replace(/\D/g, '')
  return digits ? parseInt(digits, 10) : id
}

export function extractMeasurements(text) {
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
