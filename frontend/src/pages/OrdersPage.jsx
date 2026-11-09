import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { isConnectedMode, isDemoMode, isConfigurationMissing } from '../services/apiClient.js'
import { STATUS_LABELS } from '../utils/constants.js'

function OrdersPage({ orders, loading, go, mutate, error }) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [sort, setSort] = useState('newest')
  const filtered = orders
    .filter((order) =>
      `${order.id} ${order.customer} ${order.project}`.toLowerCase().includes(query.trim().toLowerCase()) &&
      (filter === 'all' || order.status === filter))
    .sort((a, b) => {
      if (sort === 'oldest') return a.date.localeCompare(b.date)
      if (sort === 'amount-high') return b.amount - a.amount
      if (sort === 'amount-low') return a.amount - b.amount
      return b.date.localeCompare(a.date)
    })

  return (
    <div className="page-content">
      <PageHeading title="Your orders" description="Keep every project moving and see what needs attention." action={<Button icon="plus" onClick={() => go('customer/new')}>New order</Button>} />
      {isDemoMode && <DemoNotice text="The order list and status values use local demo data; changes are not sent to or saved by a workshop backend." />}
      <div className="toolbar">
        <label className="search-field">
          <Icon name="search" />
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search order, customer, or project" aria-label="Search by order, customer, or project" />
        </label>
        <label className="select-label">
          <span className="sr-only">Filter by status</span>
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">All statuses</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="select-label sort-label">
          <span className="sr-only">Sort orders</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="amount-high">Amount: high to low</option>
            <option value="amount-low">Amount: low to high</option>
          </select>
        </label>
        <span className="results-count" role="status" aria-live="polite" aria-atomic="true">{filtered.length} orders</span>
      </div>
      <div className="panel table-panel">{loading ? <LoadingState /> : isConfigurationMissing ? <p role="status" className="status-help">Backend connection not configured. No sample orders are being shown. Set VITE_API_BASE_URL, or explicitly select VITE_APP_MODE=demo.</p> : isConnectedMode && error ? <p role="alert" className="inline-error">The backend connection failed. No demo orders are being shown as real orders.</p> : <OrdersTable orders={filtered} go={go} mutate={mutate} emptyTitle={query || filter !== 'all' ? 'No matching orders' : 'No orders yet'} emptyText={query || filter !== 'all' ? 'Try changing your search or status filter.' : isConnectedMode ? 'The backend returned no orders.' : 'Orders created in the local demo will appear here.'} emptyAction={isDemoMode && !query && filter === 'all'} />}</div>
    </div>
  )
}

export default OrdersPage
