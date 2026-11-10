import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import QuoteInbox from '../components/quotes/QuoteInbox.jsx'
import { formatMoney } from '../utils/format.js'
import { isDemoMode } from '../services/apiClient.js'

function QuotesPage({ orders, quote, loading, go, mutate, refresh }) {
  const quoteOrders = orders.filter((order) => isDemoMode
    ? order.status === 'quote_sent'
    : order.status === 'pending')

  return (
    <div className="page-content">
      <PageHeading
        title="Quotes & Estimates"
        description={isDemoMode
          ? 'Review local sample orders and the active demo estimate.'
          : 'Customer requests, AI quotes and approved orders waiting for the deposit.'}
        action={<Button onClick={() => go('customer/new')}><Icon name="plus" /> Create new quote</Button>}
      />

      {!isDemoMode && <QuoteInbox onGenerated={() => void refresh?.()} />}

      {loading ? <LoadingState /> : (
        <>
          {isDemoMode && quote && (
            <section className="panel quote-list-feature">
              <div>
                <span className="eyebrow">Active quote · {quote.id}</span>
                <h2>{quote.project}</h2>
                <p>{quote.customer} · {quote.status === 'draft' ? 'Draft · estimate not validated' : 'Open estimate'}</p>
              </div>
              <strong>{formatMoney(quote.total)}</strong>
              <Button onClick={() => { window.location.hash = `#/customer/quote?id=${quote.numericId || quote.id}` }}>
                Review quote & materials <Icon name="arrow" size={15} />
              </Button>
            </section>
          )}
          <div className="section-head" style={{ marginTop: 24 }}>
            <div>
              <h2>{isDemoMode ? 'Sample orders awaiting approval' : 'Approved · awaiting deposit'}</h2>
              <p>{isDemoMode ? 'Checkout is unavailable in DEMO mode.' : 'The customer approved the quote; work starts automatically when the PayPal deposit is confirmed.'}</p>
            </div>
          </div>
          <div className="panel table-panel">
            {quoteOrders.length
              ? <OrdersTable orders={quoteOrders} go={go} mutate={mutate} />
              : <EmptyState title="No orders awaiting deposit" text="Approved quotes appear here until the customer pays the deposit." />}
          </div>
        </>
      )}
    </div>
  )
}

export default QuotesPage
