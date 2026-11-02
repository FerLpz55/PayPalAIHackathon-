import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { ACTIVE_STATUSES } from '../utils/constants.js'

function DashboardPage({ orders, loading, go }) {
  const active = orders.filter((order) => ACTIVE_STATUSES.includes(order.status)).length
  const awaitingAdvance = orders.filter((order) => ['pending', 'quote_sent'].includes(order.status)).length
  const inProduction = orders.filter((order) => order.status === 'in_progress').length
  const delivered = orders.filter((order) => order.status === 'delivered').length
  const recentOrders = [...orders].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4)

  return (
    <div className="page-content">
      <PageHeading title="Good morning, Alex" description="A clear view of every job, from first request to final payment." />
      <DemoNotice text="Orders, statuses, and totals below are sample browser data and are not connected to a workshop backend." />
      <section className="composer panel">
        <div className="composer-copy">
          <h2>What would you like to make?</h2>
          <p>Explore the local request and sample estimate flow.</p>
        </div>
        <button className="composer-action" onClick={() => go('customer/new')} aria-label="Create a new order"><Icon name="plus" /><span>New order</span></button>
        <button className="composer-text" onClick={() => go('customer/new')}>Describe the project to get started…</button>
        <div className="composer-footer">
          <span>Try the fixed-price demo estimate</span>
          <Button onClick={() => go('customer/new')}>Open quote demo <Icon name="arrow" size={15} /></Button>
        </div>
      </section>
      <section className="metric-row" aria-label="Demo order summary">
        <Metric label="Active orders" value={active} detail="Not marked delivered" />
        <Metric label="Awaiting advance" value={awaitingAdvance} detail="Pending or quote sent" tone="blue" />
        <Metric label="In production" value={inProduction} detail="Local demo order status" />
        <Metric label="Delivered" value={delivered} detail="Local demo order status" tone="green" />
      </section>
      <div className="section-head">
        <div>
          <h2>Your orders</h2>
          <p>A quick look at the latest sample orders.</p>
        </div>
        <a className="text-link" href="#/orders" onClick={(event) => { event.preventDefault(); go('orders') }}>View all orders <Icon name="arrow" size={14} /></a>
      </div>
      <div className="panel table-panel">
        {loading ? <LoadingState /> : (
          <>
            <OrdersTable orders={recentOrders} go={go} emptyText="Orders created in the local demo will appear here." />
            {recentOrders.length > 0 && <div className="table-footer">Showing {recentOrders.length} most recent of {orders.length} demo orders</div>}
          </>
        )}
      </div>
    </div>
  )
}

export default DashboardPage
