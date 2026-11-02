import Button from '../components/ui/Button.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { formatMoney } from '../utils/format.js'

function QuotesPage({ orders, quote, loading, go }) {
  const quoteOrders = orders.filter((order) => order.status === 'quote_sent' || order.status === 'pending')

  return (
    <div className="page-content">
      <PageHeading title="Quotes" description="Review estimates and keep customers informed." action={<Button icon="plus" onClick={() => go('customer/new')}>Create quote</Button>} />
      <DemoNotice text="Quotes and example totals are local demo data. They are not AI-generated, workshop-approved, or payable." />
      {loading ? <LoadingState /> : (
        <>
          {quote && (
            <section className="panel quote-list-feature">
              <div>
                <span className="eyebrow">Latest demo quote · {quote.id}</span>
                <h2>{quote.project}</h2>
                <p>{quote.customer} · Created just now · Estimate for workshop review</p>
              </div>
              <strong>{formatMoney(quote.total)}</strong>
              <Button onClick={() => go('customer/quote')}>Review quote <Icon name="arrow" size={15} /></Button>
            </section>
          )}
          <div className="section-head">
            <div>
              <h2>Waiting for approval</h2>
              <p>These customers have a quote ready for their next step.</p>
            </div>
          </div>
          <div className="panel table-panel">
            {quoteOrders.length
              ? <OrdersTable orders={quoteOrders} go={go} />
              : <EmptyState title="No quotes waiting" text="New estimates will appear here after you create them." action={<Button onClick={() => go('customer/new')}>Create a quote</Button>} />}
          </div>
        </>
      )}
    </div>
  )
}

export default QuotesPage
