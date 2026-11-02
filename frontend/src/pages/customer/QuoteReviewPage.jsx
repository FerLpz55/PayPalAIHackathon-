import { useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import DemoNotice from '../../components/ui/DemoNotice.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Icon from '../../components/ui/Icon.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import { mockApi } from '../../services/mockApi.js'
import { formatMoney } from '../../utils/format.js'

function QuoteReviewPage({ quote, orders, loading, go, mutate }) {
  const [busy, setBusy] = useState(false)
  if (loading) return <div className="customer-page"><LoadingState /></div>
  if (!quote) {
    return <div className="customer-page"><EmptyState title="No quote is ready yet" text="Describe the piece you want made to prepare an illustrative estimate." action={<Button onClick={() => go('customer/new')}>Describe your project</Button>} /></div>
  }

  const approved = quote.status === 'approved'
  const order = orders.find((item) => item.id === quote.id)
  const materials = quote.items.filter((item) => item.kind === 'material')
  const labor = quote.items.filter((item) => item.kind === 'labor')

  const payDeposit = async () => {
    setBusy(true)
    await mutate(() => mockApi.simulatePayment('deposit'), 'Demo only: no PayPal payment was sent and no money was charged.')
    setBusy(false)
    go('customer/tracking')
  }
  const approve = async () => {
    setBusy(true)
    await mutate(() => mockApi.approveQuote(), 'The quote was approved in local demo data.')
    setBusy(false)
  }

  return (
    <div className="customer-page">
      <PageHeading title="Your quote is ready" description={`Review the illustrative estimate for ${quote.customer}. Workshop approval and pricing are not connected.`} />
      <DemoNotice text="This quote, its approval, and payment actions are simulated in this browser. The estimate is not AI-generated, workshop-approved, or payable." />
      <div className="quote-review-grid">
        <section className="panel quote-breakdown">
          <div className="quote-title-row">
            <div>
              <h2>{quote.project}</h2>
              <p>{quote.measurements.width} wide · {quote.measurements.height} tall · {quote.measurements.depth} deep</p>
            </div>
            <span className={`status ${approved ? 'status-paid' : 'status-pending'}`}>{approved ? 'Approved in demo' : 'Workshop review required'}</span>
          </div>
          <h3 className="field-label">Materials</h3>
          {materials.map((item) => <DataLine key={item.label} label={item.label} value={formatMoney(item.amount)} />)}
          <h3 className="field-label labor-label">Labor</h3>
          {labor.map((item) => <DataLine key={item.label} label={item.label} value={formatMoney(item.amount)} />)}
          <div className="quote-total"><span>Estimated total</span><strong>{formatMoney(quote.total)}</strong></div>
          <p className="fine-print">Illustrative demo estimate only. A workshop must review and approve the price before it becomes payable.</p>
        </section>
        <aside className="panel payment-plan">
          <h2>Payment plan</h2>
          <div className="payment-amount">
            <span>Today · 50% deposit</span>
            <strong>{formatMoney(quote.deposit)}</strong>
            <small>Example amount for the demo flow.</small>
          </div>
          <div className="payment-amount balance-amount">
            <span>When finished · balance</span>
            <strong>{formatMoney(quote.balance)}</strong>
            <small>The deposit is subtracted from the example total.</small>
          </div>
          {quote.paymentDemo ? (
            <Button variant="success" className="full" onClick={() => go('customer/tracking')}>View demo order <Icon name="arrow" size={15} /></Button>
          ) : (
            <Button variant="paypal" className="full" disabled={busy || !approved} onClick={payDeposit}>
              {busy ? 'Updating demo…' : approved ? `Simulate ${formatMoney(quote.deposit)} deposit` : 'Waiting for workshop approval'}
            </Button>
          )}
          <p className="secure-note">Simulation only. No PayPal checkout is started and no payment is sent.</p>
          {!order && (
            <Button variant="secondary" className="full approve-button" disabled={busy || approved} onClick={approve}>
              {approved ? 'Approved in demo' : 'Approve example quote'}
            </Button>
          )}
        </aside>
      </div>
    </div>
  )
}

export default QuoteReviewPage
