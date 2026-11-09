import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import Status from '../components/ui/Status.jsx'
import { apiClient } from '../services/apiClient.js'
import { ORDER_STATUS_TRANSITIONS, STATUS_LABELS } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

function OrderDetailPage({ id, orders, loading, go, mutate }) {
  const [pendingStatus, setPendingStatus] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const order = orders.find((item) => item.id === id || String(item.orderId) === String(id))
  if (loading) return <div className="page-content"><LoadingState /></div>
  if (!order) {
    return <div className="page-content"><EmptyState title="Order not found" text="This order could not be loaded." action={<Button onClick={() => go('orders')}>Back to orders</Button>} /></div>
  }
  const transitions = ORDER_STATUS_TRANSITIONS[order.status] || []
  const availableTransitions = transitions
  const targetOrderId = order.orderId || order.id

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
          <DataLine label="Paid via PayPal" value={formatMoney(order.paid)} />
          <DataLine label="Remaining balance" value={formatMoney(Math.max(order.remainingBalance ?? (order.amount - order.paid), 0))} />
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
          <p>Verified transactions credited to this order:</p>
          <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
            <div style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 8, background: '#f8fbff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <strong>Deposit (50%)</strong>
                <span className={order.paid > 0 ? 'status-paid' : 'status-pending'} style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
                  {order.paid > 0 ? 'Confirmed via PayPal' : 'Awaiting Payment'}
                </span>
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)' }}>{formatMoney(order.deposit)}</span>
            </div>

            <div style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 8, background: '#f8fbff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <strong>Final Balance (50%)</strong>
                <span className={order.status === 'paid' || order.status === 'delivered' ? 'status-paid' : 'status-pending'} style={{ padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 600 }}>
                  {order.status === 'paid' || order.status === 'delivered' ? 'Confirmed via PayPal' : 'Due upon completion'}
                </span>
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--navy)' }}>{formatMoney(order.balance)}</span>
            </div>
          </div>
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
