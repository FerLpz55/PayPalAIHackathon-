import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { isConnectedMode, isConfigurationMissing } from '../services/apiClient.js'
import { ACTIVE_STATUSES } from '../utils/constants.js'

function DashboardPage({ orders, loading, go, mutate, error, refresh }) {
  const active = orders.filter((order) => ACTIVE_STATUSES.includes(order.status)).length
  const awaitingAdvance = orders.filter((order) => ['pending', 'quote_sent'].includes(order.status)).length
  const inProduction = orders.filter((order) => order.status === 'in_progress').length
  const delivered = orders.filter((order) => order.status === 'delivered').length
  const recentOrders = [...orders].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8)

  return (
    <div className="page-content">
      <PageHeading
        title="Workshop dashboard"
        description="A clear view of carpentry orders, active production, and verified payments."
        action={<Button onClick={() => go('customer/new')}><Icon name="plus" /> New Quote</Button>}
      />
      <section className="composer panel" style={{ marginBottom: 20 }}>
        <div className="composer-copy">
          <h2>Create a custom estimate</h2>
          <p>Describe dimensions and materials to calculate instant pricing with real store products.</p>
        </div>
        <button type="button" className="composer-text" onClick={() => go('customer/new')}>
          Describe the custom piece to start a new quote…
        </button>
      </section>
      {isConfigurationMissing ? <div className="panel"><EmptyState title="Backend connection not configured" text="No real orders are available because VITE_API_BASE_URL is missing. Configure the backend URL, or explicitly select VITE_APP_MODE=demo to view sample data." /></div> : isConnectedMode && error ? (
        <div className="panel"><EmptyState title="Workshop data is unavailable" text="The backend could not be reached. No sample orders are being shown as real orders." action={<Button onClick={refresh}>Retry connection</Button>} /></div>
      ) : (
        <>
          <section className="metric-row" aria-label={isConnectedMode ? 'Workshop order summary' : 'Demo order summary'}>
            <Metric label="Active orders" value={active} detail="Not marked delivered" />
            <Metric label="Awaiting advance" value={awaitingAdvance} detail="Pending or quote sent" tone="blue" />
            <Metric label="In production" value={inProduction} detail={isConnectedMode ? 'Current order status' : 'Local demo order status'} />
            <Metric label="Delivered" value={delivered} detail={isConnectedMode ? 'Current order status' : 'Local demo order status'} tone="green" />
          </section>
          <div className="section-head">
            <div><h2>Recent orders</h2><p>Latest active customer orders and production statuses.</p></div>
            <a className="text-link" href="#/orders" onClick={(event) => { event.preventDefault(); go('orders') }}>View all orders <Icon name="arrow" size={14} /></a>
          </div>
          <div className="panel table-panel">
            {loading ? <LoadingState /> : (
              <OrdersTable orders={recentOrders} go={go} mutate={mutate} emptyTitle="No orders yet" emptyText="Approved quotes will appear here as active workshop orders." />
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default DashboardPage
