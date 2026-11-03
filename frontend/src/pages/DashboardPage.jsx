import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { isConnectedMode, isDemoMode, isConfigurationMissing } from '../services/apiClient.js'
import { ACTIVE_STATUSES } from '../utils/constants.js'

function DashboardPage({ orders, loading, go, error, refresh }) {
  const active = orders.filter((order) => ACTIVE_STATUSES.includes(order.status)).length
  const awaitingAdvance = orders.filter((order) => ['pending', 'quote_sent'].includes(order.status)).length
  const inProduction = orders.filter((order) => order.status === 'in_progress').length
  const delivered = orders.filter((order) => order.status === 'delivered').length
  const recentOrders = [...orders].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4)

  return (
    <div className="page-content">
      <PageHeading title={isConnectedMode ? 'Workshop dashboard' : isDemoMode ? 'Good morning, Alex' : 'Workshop dashboard'} description={isConnectedMode ? 'A clear view of orders loaded from the workshop backend.' : isDemoMode ? 'A clear view of every job, from first request to final payment.' : 'Connect the workshop backend to load orders.'} />
      {isDemoMode && <DemoNotice text="Orders, statuses, and totals below are sample browser data and are not connected to a workshop backend." />}
      {isDemoMode && <section className="composer panel">
        <div className="composer-copy"><h2>What would you like to make?</h2><p>Explore the local request and sample estimate flow.</p></div>
        <button className="composer-action" onClick={() => go('customer/new')} aria-label="Create a new order"><Icon name="plus" /><span>New order</span></button>
        <button className="composer-text" onClick={() => go('customer/new')}>Describe the project to get started…</button>
        <div className="composer-footer"><span>Try the fixed-price demo estimate</span><Button onClick={() => go('customer/new')}>Open quote demo <Icon name="arrow" size={15} /></Button></div>
      </section>}
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
            <div><h2>{isConnectedMode ? 'Recent orders' : 'Your orders'}</h2><p>{isConnectedMode ? 'Latest orders returned by the workshop backend.' : 'A quick look at the latest sample orders.'}</p></div>
            <a className="text-link" href="#/orders" onClick={(event) => { event.preventDefault(); go('orders') }}>View all orders <Icon name="arrow" size={14} /></a>
          </div>
          <div className="panel table-panel">
            {loading ? <LoadingState /> : <>
              <OrdersTable orders={recentOrders} go={go} emptyTitle={isConnectedMode ? 'No orders returned' : undefined} emptyText={isConnectedMode ? 'The backend returned no orders.' : 'Orders created in the local demo will appear here.'} />
              {!isConnectedMode && recentOrders.length > 0 && <div className="table-footer">Showing {recentOrders.length} most recent of {orders.length} demo orders</div>}
            </>}
          </div>
        </>
      )}
    </div>
  )
}

export default DashboardPage
