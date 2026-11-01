import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import DemoNotice from '../../components/ui/DemoNotice.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import ProgressSteps from '../../components/ui/ProgressSteps.jsx'
import ProgressTrack from '../../components/ui/ProgressTrack.jsx'
import SuccessCallout from '../../components/ui/SuccessCallout.jsx'
import ReceiptList from '../../components/orders/ReceiptList.jsx'
import { mockApi } from '../../services/mockApi.js'
import { PROGRESS_STATUSES } from '../../utils/constants.js'
import { formatMoney } from '../../utils/format.js'

function OrderTrackingPage({ quote, orders, loading, go, mutate }) {
  if (loading) return <div className="customer-page"><LoadingState /></div>
  const order = quote && orders.find((item) => item.id === quote.id)
  if (!quote || !order) {
    return <div className="customer-page"><EmptyState title="No order to track yet" text="Prepare an estimate first to see the customer tracking flow." action={<Button onClick={() => go('customer/new')}>Start an estimate</Button>} /></div>
  }

  const payBalance = () => mutate(() => mockApi.simulatePayment('balance'), 'Demo only: no final payment was sent and no money was charged.')

  return (
    <div className="customer-page">
      <PageHeading title={`${quote.project} is in production`} description={`Order ${order.id} · Deposit received in the local demo. See a sample progress and receipt summary.`} />
      <section className="panel progress-panel"><ProgressSteps active={Math.min(3, PROGRESS_STATUSES.indexOf(order.status))} /></section>
      <div className="detail-grid tracking-grid">
        <section className="panel detail-panel">
          <div className="section-head">
            <div><h2>Material receipts</h2><p>Sample records uploaded by the workshop.</p></div>
            <span className="status status-paid">{order.receipts.length} records</span>
          </div>
          {order.receipts.length
            ? <ReceiptList receipts={order.receipts} showDetails />
            : <EmptyState title="No receipts added yet" text="Receipt records will appear here when the workshop uploads them." />}
        </section>
        <aside className="panel detail-panel">
          <h2>Your payments</h2>
          <SuccessCallout title={order.paid ? `Deposit of ${formatMoney(order.paid)} · demo record` : 'No payment record'} text="No PayPal payment has been verified." />
          <DataLine label="Estimate total" value={formatMoney(order.amount)} />
          <DataLine label="Example balance" value={formatMoney(Math.max(0, order.amount - order.paid))} />
          <ProgressTrack value={order.paid} total={order.amount} />
          {order.status === 'ready_to_finish' && <Button variant="paypal" className="full" onClick={payBalance}>Simulate balance payment</Button>}
          <p className="fine-print">The backend must verify PayPal transactions before an order is marked paid.</p>
        </aside>
      </div>
      <DemoNotice text="Order and payment states are local examples only." />
    </div>
  )
}

export default OrderTrackingPage
