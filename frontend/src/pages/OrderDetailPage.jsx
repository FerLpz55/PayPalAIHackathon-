import { useEffect, useState } from 'react'
import Button from '../components/ui/Button.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import Status from '../components/ui/Status.jsx'
import { apiClient, isDemoMode } from '../services/apiClient.js'
import { getRemainingBalance } from '../services/adapters.js'
import { FINANCIAL_STATUS_LABELS, ORDER_STATUS_TRANSITIONS, STATUS_LABELS } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

function OrderDetailPage({ id, orders, loading, go, mutate }) {
  const [pendingStatus, setPendingStatus] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [detailState, setDetailState] = useState({ id: null, loading: true, order: null, error: '' })
  const [retry, setRetry] = useState(0)
  const [customerLink, setCustomerLink] = useState('')
  const [linkBusy, setLinkBusy] = useState(false)
  const [linkError, setLinkError] = useState('')
  const detailIsCurrent = String(detailState.id) === String(id)
  const order = detailIsCurrent ? detailState.order : null
  const detailLoading = !detailIsCurrent || detailState.loading
  const detailError = detailIsCurrent ? detailState.error : ''

  useEffect(() => {
    let active = true
    apiClient.getOrder(id, { customer: false })
      .then((detail) => {
        if (active) {
          setDetailState({ id, loading: false, order: detail, error: detail ? '' : 'This order could not be found.' })
        }
      })
      .catch((error) => {
        if (active) setDetailState({ id, loading: false, order: null, error: error?.message || 'The order details could not be loaded. Try again.' })
      })
    return () => { active = false }
  }, [id, orders, retry])

  if (loading || detailLoading) return <div className="page-content"><LoadingState /></div>
  if (!order) {
    return <div className="page-content"><EmptyState title="Order details unavailable" text={detailError || 'This order could not be loaded.'} action={<div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}><Button variant="secondary" onClick={() => { setDetailState({ id, loading: true, order: null, error: '' }); setRetry((value) => value + 1) }}>Retry</Button><Button onClick={() => go('orders')}>Back to orders</Button></div>} /></div>
  }
  const transitions = ORDER_STATUS_TRANSITIONS[order.status] || []
  const availableTransitions = transitions
  const targetOrderId = order.orderId || order.id
  const remainingBalance = getRemainingBalance(order)

  const saveStatus = () => {
    const nextStatus = pendingStatus
    setPendingStatus('')
    void mutate(() => apiClient.updateStatus(targetOrderId, nextStatus), `Order ${order.id} status changed to ${STATUS_LABELS[nextStatus] || nextStatus}.`)
  }

  const issueCustomerLink = async () => {
    if (!order.quoteId) return
    setLinkBusy(true)
    setLinkError('')
    try {
      const { customerToken } = await apiClient.reissueCustomerAccess(order.quoteId)
      const base = `${window.location.origin}${window.location.pathname}`
      const link = `${base}#/customer/quote?token=${encodeURIComponent(customerToken)}&id=${order.quoteId}`
      setCustomerLink(link)
      try {
        await navigator.clipboard.writeText(link)
      } catch {
        // El enlace queda visible para copiarlo manualmente.
      }
    } catch (caught) {
      setLinkError(caught?.message || 'The customer link could not be reissued.')
    } finally {
      setLinkBusy(false)
    }
  }

  const handleDeleteOrder = async () => {
    setConfirmDelete(false)
    const deleted = await mutate(() => apiClient.deleteOrder(targetOrderId), `Order ${order.id} deleted.`)
    if (deleted) {
      go('dashboard')
    }
  }

  return (
    <div className="page-content">
      {isDemoMode && <DemoNotice text="Sample order data only. Amounts are illustrative and no PayPal transaction history is included." />}
      <PageHeading
        title={order.id}
        description={`${order.customer} · ${order.project}`}
        action={
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <Status value={order.status} />
            {order.quoteId && (
              <Button variant="secondary" onClick={() => { window.location.hash = `#/customer/quote?id=${order.quoteId}` }}>
                View Quote & Materials ↗
              </Button>
            )}
            {order.quoteId && !isDemoMode && (
              <Button variant="subtle" disabled={linkBusy} onClick={issueCustomerLink}>
                {linkBusy ? 'Issuing link…' : 'Reissue customer link'}
              </Button>
            )}
          </div>
        }
      />

      <div className="detail-grid">
        <section className="panel detail-panel">
          <div className="section-head"><div><h2>Project & Financial Details</h2><p>Official order breakdown</p></div></div>
          <DataLine label="Project" value={order.project} />
          <DataLine label="Customer" value={order.customer} />
          <DataLine label="Contracted total" value={formatMoney(order.amount)} />
          <DataLine label={isDemoMode ? 'Sample paid amount' : 'Paid via PayPal'} value={formatMoney(order.paid)} />
          <DataLine label="Remaining balance" value={formatMoney(remainingBalance)} />
          <DataLine label="Financial status" value={FINANCIAL_STATUS_LABELS[order.financialStatus] || order.financialStatus || 'Unknown'} />
          <div className="status-editor" style={{ marginTop: 20 }}>
            <label htmlFor="order-status-select" style={{ fontWeight: 600 }}>Update production milestone</label>
            <select id="order-status-select" value={order.status} disabled={!availableTransitions.length} onChange={(event) => setPendingStatus(event.target.value)}>
              <option value={order.status}>{STATUS_LABELS[order.status] || order.status} (Current)</option>
              {availableTransitions.map((choice) => <option key={choice} value={choice}>{STATUS_LABELS[choice]}</option>)}
            </select>
          </div>
          <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {order.status !== 'cancelled' && order.status !== 'delivered' && (
              <Button
                variant="subtle"
                style={{ color: '#9a5b00', border: '1px solid #f0d7a8', flex: 1 }}
                onClick={() => setPendingStatus('cancelled')}
              >
                Cancel Order
              </Button>
            )}
            <Button
              variant="subtle"
              style={{ color: '#aa3737', border: '1px solid #f9d6d6', flex: 1 }}
              onClick={() => setConfirmDelete(true)}
            >
              Delete Order
            </Button>
          </div>
        </section>
        <section className="panel detail-panel">
          <h2>Payment Records & PayPal History</h2>
          <p>{isDemoMode ? 'This sample does not include real transaction records.' : 'Verified transactions and attempts returned by the backend.'}</p>
          <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
            <div style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 8, background: '#f8fbff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <strong>Deposit (50%)</strong>
                <span className={['deposit_paid', 'paid'].includes(order.financialStatus) ? 'status-paid' : 'status-pending'} style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
                  {['deposit_paid', 'paid'].includes(order.financialStatus) ? 'Confirmed via PayPal' : 'Awaiting Payment'}
                </span>
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)' }}>{formatMoney(order.deposit)}</span>
            </div>

            {order.payments?.length > 0 && (
              <div style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 8 }}>
                <strong style={{ display: 'block', marginBottom: 6 }}>Payment attempts</strong>
                {order.payments.map((payment) => (
                  <DataLine
                    key={payment.id}
                    label={`${payment.type} · ${payment.status}`}
                    value={formatMoney(payment.amount)}
                  />
                ))}
              </div>
            )}
            {!order.payments?.length && <p className="status-help" role="status">No payment records are available for this order.</p>}

            <div style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 8, background: '#f8fbff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <strong>Final Balance (50%)</strong>
                <span className={order.financialStatus === 'paid' ? 'status-paid' : 'status-pending'} style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
                  {order.financialStatus === 'paid' ? 'Confirmed via PayPal' : 'Due upon completion'}
                </span>
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)' }}>{formatMoney(order.balance)}</span>
            </div>
          </div>
        </section>
      </div>
      {(customerLink || linkError) && (
        <section className="panel detail-panel" style={{ marginTop: 16 }}>
          <h2>Customer access link</h2>
          {linkError ? <p role="alert" className="inline-error">{linkError}</p> : null}
          {customerLink && (
            <>
              <p className="status-help">The previous link was revoked. Share this new link with the customer; it contains a bearer token and must not be published.</p>
              <input readOnly value={customerLink} aria-label="Customer access link" onFocus={(event) => event.target.select()} />
            </>
          )}
        </section>
      )}
      {pendingStatus && (
        <ConfirmDialog
          title="Update production status?"
          text={`Change order ${order.id} status to ${STATUS_LABELS[pendingStatus] || pendingStatus}.`}
          confirmLabel="Update status"
          onConfirm={saveStatus}
          onClose={() => setPendingStatus('')}
        />
      )}
      {confirmDelete && (
        <ConfirmDialog
          title="Delete order?"
          text={`Remove order ${order.id} (${order.customer}) from the workshop dashboard.`}
          confirmLabel="Delete order"
          onConfirm={handleDeleteOrder}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </div>
  )
}

export default OrderDetailPage
