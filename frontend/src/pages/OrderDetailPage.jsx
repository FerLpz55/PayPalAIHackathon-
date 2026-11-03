import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import Status from '../components/ui/Status.jsx'
import ReceiptList from '../components/orders/ReceiptList.jsx'
import { apiClient, isDemoMode } from '../services/apiClient.js'
import { ORDER_STATUS_TRANSITIONS, STATUS_LABELS } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

function OrderDetailPage({ id, orders, loading, go, mutate }) {
  const [pendingStatus, setPendingStatus] = useState('')
  const order = orders.find((item) => item.id === id)
  if (loading) return <div className="page-content"><LoadingState /></div>
  if (!order) {
    return <div className="page-content"><EmptyState title="Order not found" text={isDemoMode ? 'This order may have been removed from the local demo data.' : 'The backend did not return this order.'} action={<Button onClick={() => go('orders')}>Back to orders</Button>} /></div>
  }
  const transitions = ORDER_STATUS_TRANSITIONS[order.status] || []
  const availableTransitions = transitions.filter((status) => status !== 'delivered')
  const deliveryBlocked = transitions.includes('delivered')
  const saveStatus = () => {
    const nextStatus = pendingStatus
    setPendingStatus('')
    void mutate(() => apiClient.updateStatus(order.id, nextStatus), `Order ${order.id} status changed.`)
  }

  return (
    <div className="page-content">
      <PageHeading title={order.id} description={`${order.customer} · ${order.project}`} action={<Status value={order.status} />} />
      {isDemoMode
        ? <DemoNotice text="This order and its status, payment, and receipt values are local examples. Status edits are saved only in this browser. Delivery is unavailable here because only the backend can verify full payment." />
        : <p className="demo-notice" role="status"><span className="demo-notice-label">REAL</span><span>Order status and payment totals come from the backend. Receipt uploads are not available through the current API.</span></p>}
      <section className="panel progress-panel"><h2>{isDemoMode ? 'Current demo status' : 'Current order status'}</h2><p className="status-help">{isDemoMode ? `${STATUS_LABELS[order.status] || order.status} is a local workflow label. It does not confirm a payment or show persisted production history.` : `Backend order status: ${STATUS_LABELS[order.status] || order.status}.`}</p></section>
      <div className="detail-grid">
        <section className="panel detail-panel">
          <div className="section-head"><div><h2>Project details</h2><p>Estimate and payment summary</p></div></div>
          <DataLine label="Project" value={order.project} />
          <DataLine label="Customer" value={order.customer} />
          <DataLine label="Estimated total" value={formatMoney(order.amount)} />
          <DataLine label={isDemoMode ? 'Simulated advance' : 'Paid amount from backend'} value={formatMoney(order.paid)} />
          <DataLine label={isDemoMode ? 'Illustrative balance' : 'Remaining balance from backend'} value={order.remainingBalance == null && !isDemoMode ? 'Not provided by the backend' : formatMoney(Math.max(order.remainingBalance ?? (order.amount - order.paid), 0))} />
          <div className="status-editor">
            <label htmlFor="demo-order-status">{isDemoMode ? 'Update demo production status' : 'Update production status'}</label>
            <select id="demo-order-status" value={order.status} disabled={!availableTransitions.length} aria-describedby={deliveryBlocked ? 'delivery-requirement' : undefined} onChange={(event) => setPendingStatus(event.target.value)}>
              <option value={order.status}>{STATUS_LABELS[order.status] || order.status}</option>
              {availableTransitions.map((choice) => <option key={choice} value={choice}>{STATUS_LABELS[choice]}</option>)}
            </select>
            {deliveryBlocked
              ? <p id="delivery-requirement" className="status-help">Delivery requires backend-verified full payment. Simulated demo amounts cannot verify payment, so this action is unavailable.</p>
              : !transitions.length && <p className="status-help">{isDemoMode ? 'This sample status has no supported demo transition.' : 'No status transition is available for this order.'}</p>}
          </div>
        </section>
        <section className="panel detail-panel">
          <h2>Material receipts</h2>
          <p>{isDemoMode ? 'Sample receipt entries; no files were uploaded.' : 'Receipt upload is not available through the current backend API.'}</p>
          {isDemoMode && <>
          {order.receipts.length
            ? <ReceiptList receipts={order.receipts} />
            : <EmptyState title="No receipts yet" text="Attach purchase records from the Receipts section." action={<Button variant="secondary" onClick={() => go('receipts')}>Open receipts</Button>} />}
          <Button variant="secondary" onClick={() => go('receipts')}>Manage receipts</Button>
          </>}
        </section>
      </div>
      {pendingStatus && <ConfirmDialog title={isDemoMode ? 'Update demo production status?' : 'Update order status?'} text={isDemoMode ? `Change ${order.id} from ${STATUS_LABELS[order.status] || order.status} to ${STATUS_LABELS[pendingStatus]}. This will update local demo data only. It does not record or verify a payment.` : `Ask the backend to change ${order.id} from ${STATUS_LABELS[order.status] || order.status} to ${STATUS_LABELS[pendingStatus]}. The server remains authoritative.`} confirmLabel={isDemoMode ? 'Update demo status' : 'Update status'} onConfirm={saveStatus} onClose={() => setPendingStatus('')} />}
    </div>
  )
}

export default OrderDetailPage
