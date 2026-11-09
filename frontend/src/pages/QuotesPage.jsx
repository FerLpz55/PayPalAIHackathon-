import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import OrdersTable from '../components/orders/OrdersTable.jsx'
import { formatMoney } from '../utils/format.js'
import { apiClient } from '../services/apiClient.js'

function QuotesPage({ orders, quote, loading, go, mutate }) {
  const quoteOrders = orders.filter((order) => order.status === 'quote_sent' || order.status === 'pending')
  const [lookupId, setLookupId] = useState('')
  const [lookupError, setLookupError] = useState('')
  const [lookupBusy, setLookupBusy] = useState(false)

  const handleOpenQuoteById = async (e) => {
    e.preventDefault()
    if (!lookupId.trim()) return
    setLookupBusy(true)
    setLookupError('')
    try {
      const found = await apiClient.getQuote(lookupId.trim())
      if (found) {
        window.location.hash = `#/customer/quote?id=${found.numericId || found.id}`
      } else {
        setLookupError('Quote not found. Check the ID number.')
      }
    } catch {
      setLookupError('Could not load quote. Verify the ID.')
    } finally {
      setLookupBusy(false)
    }
  }

  return (
    <div className="page-content">
      <PageHeading
        title="Quotes & Estimates"
        description="Prepare proposals, inspect verified market materials, and review customer projects."
        action={<Button onClick={() => go('customer/new')}><Icon name="plus" /> Create new quote</Button>}
      />

      {/* Barra para abrir cualquier cotización por ID */}
      <form onSubmit={handleOpenQuoteById} className="panel" style={{ padding: '14px 18px', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 20 }}>
        <label htmlFor="quote-lookup-id" className="sr-only">Open quote by ID</label>
        <input
          id="quote-lookup-id"
          type="text"
          placeholder="Open quote by ID (e.g. 1, 2)..."
          value={lookupId}
          onChange={(e) => setLookupId(e.target.value)}
          aria-invalid={Boolean(lookupError)}
          aria-describedby={lookupError ? 'quote-lookup-error' : undefined}
          style={{ width: 240, minHeight: 44, padding: '0 12px', borderRadius: 8, border: '1px solid var(--line)', fontSize: 13 }}
        />
        <Button type="submit" variant="secondary" disabled={lookupBusy || !lookupId.trim()}>
          {lookupBusy ? 'Opening…' : 'Open Quote'}
        </Button>
        {lookupError && <span id="quote-lookup-error" role="alert" style={{ color: '#aa3737', fontSize: 12 }}>{lookupError}</span>}
      </form>

      {loading ? <LoadingState /> : (
        <>
          {quote && (
            <section className="panel quote-list-feature">
              <div>
                <span className="eyebrow">Active quote · {quote.id}</span>
                <h2>{quote.project}</h2>
                <p>{quote.customer} · Real material prices grounded with Channel3</p>
              </div>
              <strong>{formatMoney(quote.total)}</strong>
              <Button onClick={() => { window.location.hash = `#/customer/quote?id=${quote.numericId || quote.id}` }}>
                Review quote & materials <Icon name="arrow" size={15} />
              </Button>
            </section>
          )}
          <div className="section-head">
            <div>
              <h2>Pending customer approval</h2>
              <p>Orders awaiting customer deposit authorization via PayPal.</p>
            </div>
          </div>
          <div className="panel table-panel">
            {quoteOrders.length
              ? <OrdersTable orders={quoteOrders} go={go} mutate={mutate} />
              : <EmptyState title="No pending quotes" text="Create a new quote to start an estimate with live material suggestions." action={<Button onClick={() => go('customer/new')}>Create a quote</Button>} />}
          </div>
        </>
      )}
    </div>
  )
}

export default QuotesPage
