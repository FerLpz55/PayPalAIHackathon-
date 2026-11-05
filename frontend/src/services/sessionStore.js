/**
 * Almacenamiento de sesión en navegador para TallerClaro (sessionStorage).
 * Aísla credenciales temporales, tokens de cliente y seguimiento de pagos.
 */

const SESSION_KEY = 'tallerclaro.session.v1'
const PENDING_PAYMENT_KEY = 'tallerclaro.pending-payment.v1'
const COMPLETED_PAYMENT_KEY = 'tallerclaro.completed-payment.v1'

export function getSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY)
    const parsed = raw ? JSON.parse(raw) : {}
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {}
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
    // Silencioso en sandboxes con cookies/storage deshabilitados
  }
}

export function readPendingPayment() {
  try {
    const value = JSON.parse(sessionStorage.getItem(PENDING_PAYMENT_KEY) || 'null')
    return value && typeof value === 'object' ? value : null
  } catch {
    return null
  }
}

export function savePendingPayment(value) {
  try {
    sessionStorage.setItem(PENDING_PAYMENT_KEY, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

export function getPendingPayment(orderId, type) {
  const pending = readPendingPayment()
  return pending && String(pending.orderId) === String(orderId) && pending.type === type ? pending : null
}

export function getAnyPendingPayment() {
  return readPendingPayment()
}

export function getCompletedPayment(orderId, type) {
  try {
    const value = JSON.parse(sessionStorage.getItem(COMPLETED_PAYMENT_KEY) || 'null')
    return value && String(value.orderId) === String(orderId) && value.type === type ? value : null
  } catch {
    return null
  }
}

export function clearPendingPayment(paymentId) {
  const pending = readPendingPayment()
  if (!paymentId || !pending || String(pending.paymentId) !== String(paymentId)) return
  try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore */ }
  try {
    sessionStorage.setItem(
      COMPLETED_PAYMENT_KEY,
      JSON.stringify({ orderId: pending.orderId, type: pending.type, paymentId: pending.paymentId })
    )
  } catch { /* ignore */ }
}

export function discardPendingPayment(paymentId) {
  const pending = readPendingPayment()
  if (!paymentId || !pending || String(pending.paymentId) !== String(paymentId)) return
  try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore */ }
}

export function clearUnresolvedPaymentAttempt(orderId, type) {
  const pending = readPendingPayment()
  if (pending?.unresolved && String(pending.orderId) === String(orderId) && pending.type === type) {
    try { sessionStorage.removeItem(PENDING_PAYMENT_KEY) } catch { /* ignore */ }
  }
}
