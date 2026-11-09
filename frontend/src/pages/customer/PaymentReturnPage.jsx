import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import { apiClient } from '../../services/apiClient.js'
import { FINANCIAL_STATUS_LABELS } from '../../utils/constants.js'
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

function matchesSavedPayment(record, saved) {
  return String(record?.order_id) === String(saved.orderId)
    && String(record?.paypal_order_id) === String(saved.paypalOrderId)
}

function PaymentReturnPage({ cancelled = false, go, refresh }) {
  const [phase, setPhase] = useState('checking')
  const [message, setMessage] = useState('Checking the saved payment with the backend…')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(() => apiClient.getAnyPendingPayment())
  const [paymentStatus, setPaymentStatus] = useState('')
  const [financialStatus, setFinancialStatus] = useState('')
  const started = useRef(false)
  const paypalOrderId = readReturnParameters().paypalOrderId

  const loadFinancialStatus = useCallback(async (orderId) => {
    try {
      const order = await apiClient.getOrder(orderId)
      setFinancialStatus(order?.financialStatus || '')
    } catch {
      // El estado financiero es informativo; no cambia el resultado del pago.
    }
  }, [])

  const finish = useCallback(async (saved, status) => {
    setPaymentStatus(status)
    if (status === 'completed') {
      apiClient.clearPendingPayment(saved.paymentId)
      setPhase('confirmed')
      setMessage('The backend reconciled this payment with PayPal and confirmed it as completed.')
    } else if (status === 'cancelled') {
      apiClient.discardPendingPayment(saved.paymentId)
      setPhase('cancelled')
      setMessage('The backend confirmed this payment attempt as cancelled. No charge was confirmed.')
    } else if (status === 'failed') {
      apiClient.discardPendingPayment(saved.paymentId)
      setPhase('failed')
      setMessage('The backend reports that this payment attempt failed.')
    } else {
      setPhase('pending')
      setMessage('PayPal has not approved this order yet. The backend will reconcile it again from the webhook or background worker.')
    }
    await loadFinancialStatus(saved.orderId)
    await refresh?.()
  }, [loadFinancialStatus, refresh])

  const verify = useCallback(async () => {
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

    try {
      if (cancelled) {
        setPhase('cancelling')
        setMessage('Cancelling the payment attempt with the backend…')
        try {
          const result = await apiClient.cancelPayment(saved.paymentId)
          await finish(saved, String(result?.status || 'cancelled').toLowerCase())
        } catch (cancelError) {
          if (cancelError?.status !== 409) throw cancelError
          // Puede haber una captura en curso o un pago ya completado: se
          // consulta el estado real sin volver a capturar ni cancelar.
          const current = await apiClient.getPayment(saved.paymentId)
          if (!matchesSavedPayment(current, saved)) {
            setPhase('unavailable')
            setMessage('The backend payment record does not match this order. No action was taken.')
            return
          }
          await finish(saved, String(current?.status || '').toLowerCase())
        }
        return
      }

      setPhase('syncing')
      setMessage('Reconciling the payment with PayPal and the workshop backend…')
      const result = await apiClient.syncPayment(saved.paymentId)
      if (!matchesSavedPayment(result, saved)) {
        setPhase('unavailable')
        setMessage('The backend payment record does not match this order. No success is being shown.')
        return
      }
      await finish(saved, String(result?.status || '').toLowerCase())
    } catch (caught) {
      setPhase('error')
      setError(safePaymentError(caught))
    }
  }, [cancelled, finish, paypalOrderId])

  useEffect(() => {
    cleanPayPalUrlParams()
    if (started.current) return
    started.current = true
    void verify()
  }, [verify])

  const resumeCheckout = () => {
    const saved = apiClient.getAnyPendingPayment()
    if (!saved) return
    if (saved.approvalUrl && isSafePayPalUrl(saved.approvalUrl)) {
      window.location.assign(saved.approvalUrl)
      return
    }
    void verify()
  }

  const busy = phase === 'checking' || phase === 'syncing' || phase === 'cancelling'

  return (
    <div className="customer-page">
      <PageHeading title={cancelled ? 'PayPal checkout cancelled' : 'Verifying PayPal payment'} description="Payment status is determined by the workshop backend and PayPal, not by the return URL." />
      <section className="panel detail-panel" aria-live="polite">
        {busy && <LoadingState />}
        {phase === 'syncing' && <p className="status-help">Reconciling with PayPal…</p>}
        {phase === 'cancelling' && <p className="status-help">Cancelling the attempt…</p>}
        <p role={error ? 'alert' : 'status'}>{error || message}</p>
        {paymentStatus && <p>Backend payment state: <strong>{paymentStatus}</strong></p>}
        {financialStatus && <p>Order financial status: <strong>{FINANCIAL_STATUS_LABELS[financialStatus] || financialStatus}</strong></p>}
        {phase === 'confirmed' && <p className="status-paid">Payment confirmed by the backend.</p>}
        {phase === 'pending' && pending?.approvalUrl && <Button variant="paypal" onClick={resumeCheckout}>Resume the same PayPal checkout</Button>}
        {phase === 'error' && <Button variant="secondary" onClick={() => void verify()}>Check payment status again</Button>}
        {!busy && <Button variant="secondary" onClick={() => go('customer/tracking')}>Return to order tracking</Button>}
        {phase === 'unavailable' && <EmptyState title="Payment attempt unavailable" text="Reopen the secure customer link so the payment can be checked with the correct customer token." />}
      </section>
    </div>
  )
}

export default PaymentReturnPage
