import { useEffect, useState } from 'react'
import Button from '../ui/Button.jsx'
import { apiClient } from '../../services/apiClient.js'
import { isSafePayPalUrl } from '../../utils/security.js'

function formatServerAmount(amount, currency) {
  if (typeof amount !== 'number' || !Number.isFinite(amount) || typeof currency !== 'string' || !/^[A-Z]{3}$/.test(currency)) return null
  try { return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount) } catch { return null }
}

function paymentError(error, operation) {
  if (error?.status === 401 || error?.status === 403) return 'Your customer access is expired or not authorized for this payment.'
  if (error?.status === 404) return 'The payment or order was not found or is no longer accessible.'
  if (error?.status === 409) return 'The payment conflicts with the current server state. Check payment status before retrying.'
  if (error?.status === 422) return 'The payment request failed server validation. Review the order and try again if appropriate.'
  if (error?.status === 503) return 'The payment service is currently unavailable. No payment confirmation was received.'
  if (!error?.status) return 'Could not connect to the payment service. The result is unknown; check payment status before retrying.'
  return `The server could not ${operation}. No success is shown without server confirmation.`
}

function PayPalCheckout({ orderId, type, refresh }) {
  const [payment, setPayment] = useState(() => apiClient.getPendingPayment(orderId, type))
  const [busy, setBusy] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState(() => apiClient.getPendingPayment(orderId, type)?.unresolved
    ? 'A previous checkout request has an unknown result. Starting another could create a duplicate payment attempt; contact the workshop to reconcile it.'
    : '')
  const [completed, setCompleted] = useState(() => Boolean(apiClient.getCompletedPayment(orderId, type)))

  useEffect(() => {
    let active = true
    const pending = apiClient.getPendingPayment(orderId, type)
    if (!pending || pending.unresolved || !pending.paymentId) {
      return () => { active = false }
    }
    apiClient.getPayment(pending.paymentId).then((result) => {
      if (!active) return
      if (String(result?.order_id) !== String(pending.orderId) || String(result?.paypal_order_id) !== String(pending.paypalOrderId)) {
        setError('The backend payment record does not match this order. No capture is available.')
        return
      }
      const status = String(result?.status || '').toLowerCase()
      if (status === 'completed') {
        setCompleted(true)
        setMessage('The server reports this payment as completed.')
        apiClient.clearPendingPayment(pending.paymentId)
        setPayment({ ...pending, status: 'completed' })
        void refresh?.()
      } else if (['failed', 'cancelled'].includes(status)) {
        apiClient.discardPendingPayment(pending.paymentId)
        setPayment({ ...pending, status })
        setMessage(status === 'cancelled' ? 'The backend reports this payment attempt was cancelled. You can start a new attempt.' : 'The backend reports this payment attempt failed. You can start a new attempt.')
      } else if (status === 'pending') {
        setPayment({ ...pending, status })
      } else {
        setError('The backend returned an unrecognized payment state. Capture is disabled.')
      }
    }).catch((caught) => {
      if (active) setError(paymentError(caught, 'read this payment'))
    })
    return () => { active = false }
  }, [orderId, type, refresh])

  const startPayment = async () => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const next = await apiClient.createOrderPayment(orderId, type)
      setPayment(next)
      setMessage(next.approvalUrl
        ? 'Payment intent created by the backend. Continue to PayPal, then return here to reconcile it with the backend.'
        : next.checkoutIssue || 'The backend created a payment record but did not provide a PayPal approval URL. Checkout cannot continue; contact the workshop before retrying.')
    } catch (caught) {
      setError(paymentError(caught, 'start checkout'))
    } finally {
      setBusy(false)
    }
  }

  const verifyPayment = async () => {
    if (!payment?.paymentId) return
    setCapturing(true)
    setError('')
    setMessage('Reconciling payment status with PayPal and the workshop backend…')
    try {
      const result = await apiClient.syncPayment(payment.paymentId)
      const status = String(result?.status || '').toLowerCase()
      if (status === 'completed') {
        setCompleted(true)
        setMessage('Payment reconciled and confirmed by PayPal through the backend.')
        apiClient.clearPendingPayment(payment.paymentId)
        setPayment({ ...payment, status: 'completed' })
        void refresh?.()
      } else if (status === 'cancelled' || status === 'failed') {
        apiClient.discardPendingPayment(payment.paymentId)
        setPayment({ ...payment, status })
        setMessage(`The backend reports this payment attempt as ${status}. You can start a new attempt.`)
        void refresh?.()
      } else {
        setMessage('The payment is still pending in PayPal. The backend will reconcile it again from the PayPal webhook or background worker.')
      }
    } catch (caught) {
      setError(paymentError(caught, 'reconcile the payment'))
    } finally {
      setCapturing(false)
    }
  }

  const cancelAttempt = async () => {
    if (!payment?.paymentId) return
    setCancelling(true)
    setError('')
    setMessage('Cancelling this payment attempt with the backend…')
    try {
      const result = await apiClient.cancelPayment(payment.paymentId)
      apiClient.discardPendingPayment(payment.paymentId)
      setPayment({ ...payment, status: String(result?.status || 'cancelled').toLowerCase() })
      setMessage('The backend confirmed the attempt as cancelled. No charge was confirmed.')
      void refresh?.()
    } catch (caught) {
      setError(paymentError(caught, 'cancel this payment attempt'))
    } finally {
      setCancelling(false)
    }
  }

  const redirectToPayPal = () => {
    if (!isSafePayPalUrl(payment?.approvalUrl)) {
      setError('The PayPal checkout URL is invalid or untrusted. Redirect cancelled.')
      return
    }
    setMessage('Opening PayPal Checkout in a secure window. Complete your payment and click "Verify & Confirm Payment" below.')
    window.open(payment.approvalUrl, '_blank', 'noopener,noreferrer')
  }

  const closed = ['failed', 'cancelled'].includes(String(payment?.status || '').toLowerCase())

  return (
    <section className="paypal-checkout" aria-labelledby={`paypal-${type}-heading`}>
      <h3 id={`paypal-${type}-heading`}>{type === 'deposit' ? 'Pay deposit with PayPal' : 'Pay remaining balance with PayPal'}</h3>
      {payment && formatServerAmount(payment.amount, payment.currency) && <p>Amount to authorize: <strong>{formatServerAmount(payment.amount, payment.currency)}</strong></p>}
      {!payment && !completed && <Button variant="paypal" className="full" disabled={busy || Boolean(apiClient.getPendingPayment(orderId, type)?.unresolved)} onClick={startPayment}>{busy ? 'Connecting to PayPal…' : 'Start PayPal Checkout'}</Button>}
      {payment && !completed && payment.approvalUrl && !closed && (
        <div style={{ display: 'grid', gap: 10 }}>
          <Button variant="paypal" className="full" disabled={busy || capturing || cancelling} onClick={redirectToPayPal}>
            1. Open PayPal Checkout ↗
          </Button>
          <Button variant="success" className="full" disabled={capturing || cancelling} onClick={verifyPayment}>
            {capturing ? 'Reconciling with PayPal…' : '2. Verify & Confirm Payment'}
          </Button>
          <Button variant="subtle" className="full" disabled={capturing || cancelling} onClick={cancelAttempt}>
            {cancelling ? 'Cancelling…' : 'Cancel this payment attempt'}
          </Button>
          <p className="status-help">Verification reconciles the payment with PayPal. The backend only captures an order that PayPal has approved; a pending result is retried by the webhook or the background worker.</p>
        </div>
      )}
      {payment && !completed && !payment.approvalUrl && <p role="alert" className="status-help">PayPal checkout is unavailable because the backend did not return a safe approval URL.</p>}
      {payment && !completed && closed && <Button variant="paypal" className="full" disabled={busy} onClick={() => { setPayment(null); setMessage('Starting a new attempt.'); void startPayment() }}>Start a new payment attempt</Button>}
      {message && <p role="status" className="status-help">{message}</p>}
      {error && <p role="alert" className="error-message">{error}</p>}
      {completed && <p role="status" className="status-paid">Payment verified & confirmed by workshop.</p>}
    </section>
  )
}

export default PayPalCheckout
