import Button from '../components/ui/Button.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import ProgressSteps from '../components/ui/ProgressSteps.jsx'
import Status from '../components/ui/Status.jsx'
import ReceiptList from '../components/orders/ReceiptList.jsx'
import { mockApi } from '../services/mockApi.js'
import { ORDER_STATUSES, PROGRESS_STATUSES, STATUS_LABELS } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

function OrderDetailPage({ id, orders, loading, go, mutate }) {
  const order = orders.find((item) => item.id === id)
  if (loading) return <div className="page-content"><LoadingState /></div>
  if (!order) {
    return <div className="page-content"><EmptyState title="Order not found" text="This order may have been removed from the local demo data." action={<Button onClick={() => go('orders')}>Back to orders</Button>} /></div>
  }
  const step = Math.max(0, PROGRESS_STATUSES.indexOf(order.status))

  return (
    <div className="page-content">
      <PageHeading title={order.id} description={`${order.customer} · ${order.project}`} action={<Status value={order.status} />} />
      <DemoNotice text="This order and its status, payment, and receipt values are local examples. Status edits are not persisted to a backend." />
      <section className="panel progress-panel"><h2>Order progress</h2><ProgressSteps active={step} /></section>
      <div className="detail-grid">
        <section className="panel detail-panel">
          <div className="section-head"><div><h2>Project details</h2><p>Estimate and payment summary</p></div></div>
          <DataLine label="Project" value={order.project} />
          <DataLine label="Customer" value={order.customer} />
          <DataLine label="Estimated total" value={formatMoney(order.amount)} />
          <DataLine label="Simulated advance" value={formatMoney(order.paid)} />
          <DataLine label="Illustrative balance" value={formatMoney(Math.max(order.amount - order.paid, 0))} />
          <label className="status-editor">
            Update demo status
            <select value={order.status} onChange={(event) => mutate(() => mockApi.updateStatus(order.id, event.target.value), `Order ${order.id} status updated in demo data.`)}>
              {ORDER_STATUSES.map((choice) => <option key={choice} value={choice}>{STATUS_LABELS[choice]}</option>)}
            </select>
          </label>
        </section>
        <section className="panel detail-panel">
          <h2>Material receipts</h2>
          <p>Sample receipt entries; no files were uploaded.</p>
          {order.receipts.length
            ? <ReceiptList receipts={order.receipts} />
            : <EmptyState title="No receipts yet" text="Attach purchase records from the Receipts section." action={<Button variant="secondary" onClick={() => go('receipts')}>Open receipts</Button>} />}
          <Button variant="secondary" onClick={() => go('receipts')}>Manage receipts</Button>
        </section>
      </div>
    </div>
  )
}

export default OrderDetailPage
