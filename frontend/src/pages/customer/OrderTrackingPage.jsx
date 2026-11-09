import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import PayPalCheckout from '../../components/customer/PayPalCheckout.jsx'
import { isConnectedMode, isDemoMode } from '../../services/apiClient.js'
import { formatMoney } from '../../utils/format.js'

function OrderTrackingPage({ quote, orders, loading, go, refresh }) {
  if (loading) return <div className="customer-page"><LoadingState /></div>
  const order = quote && orders.find((item) => String(item.quoteId || item.id) === String(quote.numericId || quote.id))
  if (!quote || !order) {
    return <div className="customer-page"><EmptyState title="No order to track yet" text={isConnectedMode ? 'No customer-authorized order was returned. Reopen the secure customer link or contact the workshop.' : 'Prepare an estimate first to see the demo tracking flow.'} action={isDemoMode && <Button onClick={() => go('customer/new')}>Start an estimate</Button>} /></div>
  }

  return (
    <div className="customer-page">
      <PageHeading
        title={`Order tracking · ${quote.project}`}
        description={`Order ${order.id} · Production status and verified payments.`}
        action={
          <Button variant="secondary" onClick={() => { window.location.hash = `#/customer/quote?id=${quote.numericId || quote.id}` }}>
            View Quote & Material References ↗
          </Button>
        }
      />
      <div className="detail-grid tracking-grid">
        <section className="panel detail-panel">
          <h2>Production & Order Status</h2>
          <DataLine label="Order code" value={order.id} />
          <DataLine label="Current status" value={order.status} />
          <DataLine label="Contracted total" value={formatMoney(order.amount)} />
          <DataLine label="Verified paid" value={formatMoney(order.paid)} />
          <DataLine label="Remaining balance" value={formatMoney(Math.max(order.remainingBalance ?? (order.amount - order.paid), 0))} />
          <h3 style={{ marginTop: 20, marginBottom: 8 }}>Transaction History</h3>
          {order.payments?.length ? (
            order.payments.map((payment) => (
              <DataLine key={payment.id} label={`${payment.type} · ${payment.status}`} value={formatMoney(payment.amount)} />
            ))
          ) : (
            <p className="status-help">No payment records yet.</p>
          )}
        </section>
        <aside className="panel detail-panel">
          <h2>Pay remaining balance</h2>
          {order.remainingBalance > 0 && order.orderId ? (
            <PayPalCheckout orderId={order.orderId} type="balance" refresh={refresh} />
          ) : (
            <p className="status-help" style={{ color: 'var(--green)', fontWeight: 600 }}>This order has no balance due.</p>
          )}
        </aside>
      </div>
    </div>
  )
}

export default OrderTrackingPage
