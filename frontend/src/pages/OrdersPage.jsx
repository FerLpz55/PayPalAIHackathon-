import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { STATUS_LABELS } from '../utils/constants.js'

function OrdersPage({ orders, loading, go }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const filtered = orders.filter((order) =>
    `${order.id} ${order.customer} ${order.project}`.toLowerCase().includes(query.toLowerCase()) &&
    (filter === 'all' || order.status === filter))

  return (
    <div className="page-content">
      <PageHeading title="Your orders" description="Keep every project moving and see what needs attention." action={<Button icon="plus" onClick={() => go('customer/new')}>New order</Button>} />
      <div className="toolbar">
        <label className="search-field">
          <Icon name="search" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search orders or customers" aria-label="Search orders or customers" />
        </label>
        <label className="select-label">
          <span className="sr-only">Filter by status</span>
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <span className="results-count" role="status" aria-live="polite" aria-atomic="true">{filtered.length} orders</span>
      </div>
      <div className="panel table-panel">{loading ? <LoadingState /> : <OrdersTable orders={filtered} go={go} />}</div>
      <DemoNotice text="Status updates are saved in local demo data and do not contact a backend." />
    </div>
  )
}

export default OrdersPage
