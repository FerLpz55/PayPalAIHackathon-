import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import PayPalCheckout from '../../components/customer/PayPalCheckout.jsx'
import DemoNotice from '../../components/ui/DemoNotice.jsx'
import { isConnectedMode, isDemoMode } from '../../services/apiClient.js'
import { getRemainingBalance } from '../../services/adapters.js'
import { formatMoney } from '../../utils/format.js'
import { STATUS_LABELS } from '../../utils/constants.js'

function OrderTrackingPage({ quote, orders, loading, go, refresh }) {
  if (loading) return <div className="customer-page"><LoadingState /></div>
  const order = quote && orders.find((item) => String(item.quoteId || item.id) === String(quote.numericId || quote.id))
  if (!quote || !order) {
    return <div className="customer-page"><EmptyState title="No order to track yet" text={isConnectedMode ? 'No customer-authorized order was returned. Reopen the secure customer link or contact the workshop.' : 'Prepare an estimate first to see the demo tracking flow.'} action={isDemoMode && <Button onClick={() => go('customer/new')}>Start an estimate</Button>} /></div>
  }
  const remainingBalance = getRemainingBalance(order)
  const checkoutUnavailable = ['cancelled', 'deleted'].includes(String(order.status || '').toLowerCase())

  return (
    <div className="customer-page">
      {isDemoMode && <DemoNotice text="Demo order only. The amounts and payment history below are illustrative; no real payment is available here." />}
      <PageHeading
        title={`Order tracking · ${quote.project}`}
        description={isDemoMode ? `Order ${order.id} · sample production status and illustrative amounts.` : `Order ${order.id} · production status and backend payment records.`}
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
          <DataLine label="Current status" value={STATUS_LABELS[order.status] || order.status} />
          <DataLine label="Contracted total" value={formatMoney(order.amount)} />
          <DataLine label={isDemoMode ? 'Sample paid amount' : 'Verified paid'} value={formatMoney(order.paid)} />
          <DataLine label="Remaining balance" value={formatMoney(remainingBalance)} />
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
          <h2>{checkoutUnavailable ? 'Checkout unavailable' : 'Pay remaining balance'}</h2>
          {isDemoMode ? (
            <p className="status-help" role="status">Demo mode does not create or collect payments. Use the sample amounts for interface review only.</p>
          ) : checkoutUnavailable ? (
            <p className="status-help" role="alert">Checkout is unavailable because this order was cancelled or deleted. Contact the workshop if you believe this is incorrect.</p>
          ) : remainingBalance == null ? (
            <p className="status-help" role="alert">The balance is unavailable, so checkout cannot start.</p>
          ) : remainingBalance > 0 && order.orderId ? (
            <PayPalCheckout orderId={order.orderId} type="balance" refresh={refresh} />
          ) : remainingBalance > 0 ? (
            <p className="status-help" role="alert">The backend did not return an order ID. Checkout cannot start.</p>
          ) : (
            <p className="status-help" style={{ color: 'var(--green)', fontWeight: 600 }}>This order has no balance due.</p>
          )}
        </aside>
      </div>
    </div>
  )
}

export default OrderTrackingPage
