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
import { ORDER_STATUS_TRANSITIONS, STATUS_LABELS } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

function OrderDetailPage({ id, orders, loading, go, mutate }) {
  const [pendingStatus, setPendingStatus] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [detailState, setDetailState] = useState({ id: null, loading: true, order: null, error: '' })
  const [retry, setRetry] = useState(0)
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
          <h2>Payment Records</h2>
          <p>{isDemoMode ? 'This sample does not include transaction records.' : 'Transactions returned for this order by the backend.'}</p>
          {order.payments?.length ? (
            <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
              {order.payments.map((payment) => (
                <DataLine key={payment.id} label={`${payment.type || 'Payment'} · ${payment.status || 'Status unavailable'}`} value={formatMoney(payment.amount)} />
              ))}
            </div>
          ) : <p className="status-help" role="status">No payment records are available for this order.</p>}
        </section>
      </div>
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
