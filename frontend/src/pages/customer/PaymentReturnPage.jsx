import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import { apiClient } from '../../services/apiClient.js'
import { cleanPayPalUrlParams, isSafePayPalUrl } from '../../utils/security.js'

function readReturnParameters() {
  const search = new URLSearchParams(window.location.search)
  const hashQuery = window.location.hash.split('?').slice(1).join('?')
  const hashParams = new URLSearchParams(hashQuery)
  return {
    paypalOrderId: search.get('token') || hashParams.get('token'),
  }
}

function safePaymentError(error) {
  if (error?.status === 401 || error?.status === 403) return 'Your customer access is expired or is not authorized to verify this payment.'
  if (error?.status === 404) return 'The saved payment could not be found or is no longer accessible.'
  if (error?.status === 409) return 'The backend has not confirmed this payment as capturable. Check its state before trying again.'
  if (error?.status === 503) return 'The payment service is unavailable. The result remains unverified.'
  if (!error?.status) return 'The connection was interrupted. The payment result is unknown; check the backend before retrying.'
  return 'The backend could not verify the payment. No success is being shown.'
}

function PaymentReturnPage({ cancelled = false, go, refresh }) {
  const [phase, setPhase] = useState('checking')
  const [message, setMessage] = useState('Checking the saved payment with the backend…')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(() => apiClient.getAnyPendingPayment())
  const [paymentStatus, setPaymentStatus] = useState('')
  const started = useRef(false)
  const paypalOrderId = readReturnParameters().paypalOrderId

  const verify = useCallback(async ({ shouldCapture }) => {
    const saved = apiClient.getAnyPendingPayment()
    setPending(saved)
    setError('')
    if (!saved || saved.unresolved || !saved.paymentId || !saved.paypalOrderId) {
      setPhase('unavailable')
      setMessage('This browser has no recoverable payment attempt. No payment lookup or new attempt was made.')
      return
    }
    if (paypalOrderId && String(paypalOrderId) !== String(saved.paypalOrderId)) {
      setPhase('unavailable')
      setMessage('The PayPal return does not match the saved payment attempt. No capture was requested.')
      return
    }

    setPhase('checking')
    setMessage('Verifying payment identity and status with the backend…')
    try {
      const current = await apiClient.getPayment(saved.paymentId)
      if (String(current?.order_id) !== String(saved.orderId) || String(current?.paypal_order_id) !== String(saved.paypalOrderId)) {
        setPhase('unavailable')
        setMessage('The backend payment record does not match this order. No capture was requested.')
        return
      }
      const status = String(current?.status || '').toLowerCase()
      setPaymentStatus(status)
      if (status === 'completed') {
        apiClient.clearPendingPayment(saved.paymentId)
        setPhase('confirmed')
        setMessage('The backend confirmed this payment as completed.')
        await refresh?.()
        return
      }
      if (status === 'failed' || status === 'cancelled') {
        apiClient.discardPendingPayment(saved.paymentId)
        setPhase(status)
        setMessage(status === 'cancelled' ? 'The backend reports this payment attempt as cancelled.' : 'The backend reports that this payment attempt failed.')
        return
      }
      if (status !== 'pending') {
        setPhase('unavailable')
        setMessage('The backend returned an unrecognized payment state. No success is being shown.')
        return
      }
      if (cancelled) {
        setPhase('cancelled')
        setMessage('You returned from PayPal cancellation. The backend still reports a pending attempt; no capture was requested.')
        return
      }
      if (!shouldCapture) {
        setPhase('pending')
        setMessage('The payment is still pending. Use the backend verification action to retry capture after PayPal approval.')
        return
      }

      setPhase('capturing')
      setMessage('PayPal returned to the approval route. Asking the backend to capture and verify…')
      const captured = await apiClient.capturePayment(saved.paymentId)
      const verified = await apiClient.getPayment(saved.paymentId)
      if (String(verified?.order_id) !== String(saved.orderId) || String(verified?.paypal_order_id) !== String(saved.paypalOrderId) || String(verified?.status || '').toLowerCase() !== 'completed') {
        throw new Error('The captured payment is not confirmed by a matching completed backend payment record.')
      }
      setPaymentStatus(String(verified.status || captured.status || '').toLowerCase())
      apiClient.clearPendingPayment(saved.paymentId)
      setPhase('confirmed')
      setMessage('The backend verified and captured this payment.')
      await refresh?.()
    } catch (caught) {
      setPhase('error')
      setError(safePaymentError(caught))
    }
  }, [cancelled, paypalOrderId, refresh])

  useEffect(() => {
    cleanPayPalUrlParams()
    if (started.current) return
    started.current = true
    void verify({ shouldCapture: !cancelled })
  }, [cancelled, verify])

  // Pago confirmado por el backend ⇒ llevar al cliente al seguimiento del pedido.
  useEffect(() => {
    if (phase !== 'confirmed') return undefined
    const timer = window.setTimeout(() => go('customer/tracking'), 1500)
    return () => window.clearTimeout(timer)
  }, [phase, go])

  const retryPayment = () => {
    const saved = apiClient.getAnyPendingPayment()
    if (!saved) return
    if (cancelled && saved.approvalUrl && isSafePayPalUrl(saved.approvalUrl)) {
      window.location.assign(saved.approvalUrl)
      return
    }
    void verify({ shouldCapture: true })
  }

  return (
    <div className="customer-page">
      <PageHeading title={cancelled ? 'PayPal checkout cancelled' : 'Verifying PayPal payment'} description="Payment status is determined by the workshop backend, not by the return URL." />
      <section className="panel detail-panel" aria-live="polite">
        {phase === 'checking' || phase === 'capturing' ? <LoadingState /> : null}
        {(phase === 'checking' || phase === 'capturing') && <p className="status-help">{phase === 'capturing' ? 'Capturing payment with the backend…' : 'Checking payment with the backend…'}</p>}
        <p role={error ? 'alert' : 'status'}>{error || message}</p>
        {paymentStatus && <p>Backend payment state: <strong>{paymentStatus}</strong></p>}
        {phase === 'confirmed' && <p className="status-paid">Payment confirmed by the backend.</p>}
        {(phase === 'cancelled' || phase === 'pending') && pending?.approvalUrl && <Button variant="paypal" onClick={retryPayment}>Resume the same PayPal checkout</Button>}
        {phase === 'error' && <Button variant="secondary" onClick={() => void verify({ shouldCapture: !cancelled })}>Check payment status again</Button>}
        {(phase === 'confirmed' || phase === 'cancelled' || phase === 'failed' || phase === 'pending' || phase === 'unavailable' || phase === 'error') && <Button variant="secondary" onClick={() => go('customer/tracking')}>Return to order tracking</Button>}
        {phase === 'unavailable' && <EmptyState title="Payment attempt unavailable" text="Reopen the secure customer link so the payment can be checked with the correct customer token." />}
      </section>
    </div>
  )
}

export default PaymentReturnPage
