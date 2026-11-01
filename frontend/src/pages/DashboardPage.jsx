import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { ACTIVE_STATUSES } from '../utils/constants.js'
import { formatMoney } from '../utils/format.js'

const pad = (value) => String(value).padStart(2, '0')

function DashboardPage({ orders, loading, go }) {
  const active = orders.filter((order) => ACTIVE_STATUSES.includes(order.status)).length
  const review = orders.filter((order) => order.status === 'quote_sent').length
  const received = orders.reduce((sum, order) => sum + order.paid, 0)
  const attention = orders.filter((order) => order.status === 'ready_to_finish').length

  return (
    <div className="page-content">
      <PageHeading title="Good morning, Alex" description="A clear view of every job, from first request to final payment." />
      <section className="composer panel">
        <div className="composer-copy">
          <h2>What would you like to make?</h2>
          <p>Start an order and prepare a quote for your customer.</p>
        </div>
        <button className="composer-action" onClick={() => go('customer/new')} aria-label="Create a new order"><Icon name="plus" /><span>New order</span></button>
        <button className="composer-text" onClick={() => go('customer/new')}>Describe the project to get started…</button>
        <div className="composer-footer">
          <span>Type a request to create a demo quote</span>
          <Button onClick={() => go('customer/new')}>Create with AI <Icon name="arrow" size={15} /></Button>
        </div>
      </section>
      <section className="metric-row" aria-label="Workshop summary">
        <Metric label="Active orders" value={pad(active)} detail="Across all stages" />
        <Metric label="Quotes to review" value={pad(review)} detail="Waiting for an advance" tone="blue" />
        <Metric label="Payments received" value={formatMoney(received)} detail="Illustrative demo figures" tone="green" />
        <Metric label="Needs attention" value={pad(attention)} detail="Ready to finish" />
      </section>
      <div className="section-head">
        <div>
          <h2>Your orders</h2>
          <p>A quick look at the work moving through your shop.</p>
        </div>
        <a className="text-link" href="#/orders" onClick={(event) => { event.preventDefault(); go('orders') }}>View all orders <Icon name="arrow" size={14} /></a>
      </div>
      <div className="panel table-panel">
        {loading ? <LoadingState /> : (
          <>
            <OrdersTable orders={orders.slice(0, 4)} go={go} />
            <div className="table-footer">Showing {Math.min(4, active)} of {active} active orders</div>
          </>
        )}
      </div>
      <DemoNotice text="Sample orders and totals are stored in this browser for demonstration. They are not connected to a workshop backend." />
    </div>
  )
}

export default DashboardPage
