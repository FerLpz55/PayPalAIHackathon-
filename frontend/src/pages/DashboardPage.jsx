import { useEffect, useState } from 'react'
import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { apiClient, isConnectedMode, isConfigurationMissing, isDemoMode } from '../services/apiClient.js'

function DashboardPage({ orders, loading, go, mutate, error, refresh }) {
  const [summary, setSummary] = useState(null)
  const [summaryLoading, setSummaryLoading] = useState(true)
  const [summaryError, setSummaryError] = useState('')
  const [summaryRetry, setSummaryRetry] = useState(0)
  const recentOrders = [...orders].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8)

  useEffect(() => {
    let active = true
    apiClient.getFinancialSummary()
      .then((result) => {
        if (active) {
          setSummary(result)
          setSummaryError('')
        }
      })
      .catch((caught) => {
        if (active) {
          setSummary(null)
          setSummaryError(caught?.message || 'The dashboard summary could not be loaded.')
        }
      })
      .finally(() => {
        if (active) setSummaryLoading(false)
      })
    return () => { active = false }
  }, [summaryRetry])

  const metric = (value) => summaryLoading ? '…' : summaryError ? '—' : value ?? '—'

  return (
    <div className="page-content">
      {isDemoMode && <DemoNotice text="Dashboard values come from local sample orders. They are not live workshop or payment data." />}
      <PageHeading
        title="Workshop dashboard"
        description={isDemoMode ? 'Explore the local sample workshop dashboard.' : 'Review orders, production status, and backend payment totals.'}
        action={<Button onClick={() => go('customer/new')}><Icon name="plus" /> New Quote</Button>}
      />
      <section className="composer panel" style={{ marginBottom: 20 }}>
        <div className="composer-copy">
          <h2>Create a custom estimate</h2>
          <p>{isDemoMode ? 'Open the request form to explore the local estimate demo.' : 'Open the request form to start a project request.'}</p>
        </div>
        <button type="button" className="composer-text" onClick={() => go('customer/new')}>
          Describe the custom piece to start a new quote…
        </button>
      </section>
      {summaryError && (
        <section className="panel inline-error" role="alert" style={{ marginBottom: 16 }}>
          <p>Workshop summary unavailable: {summaryError}</p>
          <Button variant="secondary" onClick={() => { setSummaryLoading(true); setSummaryError(''); setSummaryRetry((value) => value + 1) }}>Retry summary</Button>
        </section>
      )}
      {isConfigurationMissing ? <div className="panel"><EmptyState title="Backend connection not configured" text="No real orders are available because VITE_API_BASE_URL is missing. Configure the backend URL, or explicitly select VITE_APP_MODE=demo to view sample data." /></div> : isConnectedMode && error ? (
        <div className="panel"><EmptyState title="Workshop data is unavailable" text="The backend could not be reached. No sample orders are being shown as real orders." action={<Button onClick={refresh}>Retry connection</Button>} /></div>
      ) : (
        <>
          <section className="metric-row" aria-label={isConnectedMode ? 'Workshop order summary' : 'Demo order summary'}>
            <Metric label="Active orders" value={metric(summary?.activeOrdersCount)} detail={isDemoMode ? 'Local sample summary' : 'Backend aggregate'} />
            <Metric label="Awaiting advance" value={metric(summary?.awaitingDeposit)} detail={isDemoMode ? 'Pending or quote sent' : 'Backend-reported count'} tone="blue" />
            <Metric label="Orders with balance due" value={metric(summary?.ordersWithBalanceDue)} detail={isDemoMode ? 'Local sample summary' : 'Backend aggregate'} />
            <Metric label="Delivered" value={metric(summary?.deliveredOrdersCount)} detail={isDemoMode ? 'Local sample summary' : 'Backend aggregate'} tone="green" />
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
