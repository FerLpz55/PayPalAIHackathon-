import { useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import DemoNotice from '../../components/ui/DemoNotice.jsx'
import PayPalCheckout from '../../components/customer/PayPalCheckout.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import Icon from '../../components/ui/Icon.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import { apiClient, isConnectedMode, isDemoMode, isConfigurationMissing } from '../../services/apiClient.js'
import { formatMoney } from '../../utils/format.js'

function QuoteReviewPage({ quote, orders, loading, go, mutate, refresh }) {
  const [busy, setBusy] = useState(false)
  const [additionalInfo, setAdditionalInfo] = useState('')

  if (loading) return <div className="customer-page"><LoadingState /></div>
  if (isConfigurationMissing) return <div className="customer-page"><EmptyState title="Backend connection not configured" text="Quotes and payment actions are unavailable until VITE_API_BASE_URL is configured. No sample quote is being shown as real." /></div>
  if (!quote) {
    return <div className="customer-page"><EmptyState title="No quote is ready yet" text="Describe the piece you want made to prepare an illustrative estimate." action={<Button onClick={() => go('customer/new')}>Describe your project</Button>} /></div>
  }

  const approved = quote.status === 'approved'
  const isNeedsInfo = quote.status === 'needs_information'
  const order = orders.find((item) => String(item.quoteId || item.id) === String(quote.numericId || quote.id))
  const items = quote.items || []
  const materials = items.filter((item) => item.kind === 'material')
  const labor = items.filter((item) => item.kind === 'labor')

  const payDepositDemo = async () => {
    setBusy(true)
    await mutate(() => apiClient.simulatePayment('deposit'), 'Demo only: no PayPal payment was sent and no money was charged.')
    setBusy(false)
    go('customer/tracking')
  }

  const approve = async () => {
    setBusy(true)
    await mutate(() => apiClient.approveQuote(quote.numericId || quote.id), 'The quote was approved.')
    setBusy(false)
  }

  const handleMissingInfoSubmit = async (e) => {
    e.preventDefault()
    if (!additionalInfo.trim()) return
    setBusy(true)
    await mutate(
      () => apiClient.submitMissingInfo(quote.numericId || quote.id, additionalInfo.trim()),
      'Additional information submitted successfully.'
    )
    setAdditionalInfo('')
    setBusy(false)
  }

  const measurementsText = `${quote.measurements?.width ?? '-'} wide · ${quote.measurements?.height ?? '-'} tall · ${quote.measurements?.depth ?? '-'} deep`

  return (
    <div className="customer-page">
      <PageHeading title="Your quote is ready" description={`Review the estimate for ${quote.customer}. Workshop review and approval required before order confirmation.`} />
      {isConnectedMode
        ? <p className="demo-notice" role="status"><span className="demo-notice-label">REAL</span><span>Quote and order information come from the backend. Payments require server verification.</span></p>
        : <DemoNotice text="This quote, its approval, and payment actions are simulated in this browser. No order or payment is persisted by a server." />}
      <div className="quote-review-grid">
        <section className="panel quote-breakdown">
          <div className="quote-title-row">
            <div>
              <h2>{quote.project}</h2>
              <p>{measurementsText}</p>
            </div>
            <span className={`status ${approved ? 'status-paid' : isNeedsInfo ? 'status-pending' : 'status-pending'}`}>
              {approved ? 'Approved' : isNeedsInfo ? 'Information needed' : 'Workshop review required'}
            </span>
          </div>

          {isNeedsInfo && (
            <div className="info-callout" style={{ borderColor: '#ead8a7', background: '#fffaf0', margin: '0 0 18px' }}>
              <strong style={{ color: '#8a5a00' }}>Additional details required</strong>
              <p style={{ margin: '6px 0 10px', color: 'var(--text)' }}>
                The workshop needs more details to accurately estimate your project:
              </p>
              {quote.missing_info && quote.missing_info.length > 0 && (
                <ul style={{ margin: '0 0 14px', paddingLeft: '20px', color: '#52677f' }}>
                  {quote.missing_info.map((item, idx) => (
                    <li key={idx}>{item}</li>
                  ))}
                </ul>
              )}
              <form onSubmit={handleMissingInfoSubmit}>
                <label className="field-label" htmlFor="additional-info-input" style={{ marginBottom: '6px' }}>
                  Provide missing details
                </label>
                <textarea
                  id="additional-info-input"
                  rows="3"
                  value={additionalInfo}
                  onChange={(e) => setAdditionalInfo(e.target.value)}
                  placeholder="Provide dimensions, materials, or details requested above..."
                  disabled={busy}
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line)', marginBottom: '10px' }}
                />
                <Button type="submit" disabled={busy || !additionalInfo.trim()}>
                  {busy ? 'Submitting…' : 'Send missing information'}
                </Button>
              </form>
            </div>
          )}

          <h3 className="field-label">Materials</h3>
          {materials.length > 0 ? (
            materials.map((item) => <DataLine key={item.id || item.label} label={item.label} value={formatMoney(item.amount)} />)
          ) : (
            <p className="status-help" style={{ margin: '4px 0 12px' }}>{isNeedsInfo ? 'Materials will be estimated once missing details are provided.' : 'No material line items.'}</p>
          )}

          <h3 className="field-label labor-label">Labor</h3>
          {labor.length > 0 ? (
            labor.map((item) => <DataLine key={item.id || item.label} label={item.label} value={formatMoney(item.amount)} />)
          ) : (
            <p className="status-help" style={{ margin: '4px 0 12px' }}>{isNeedsInfo ? 'Labor will be calculated once project scope is confirmed.' : 'No labor line items.'}</p>
          )}

          <div className="quote-total"><span>Estimated total</span><strong>{formatMoney(quote.total)}</strong></div>

          {quote.assumptions && quote.assumptions.length > 0 && (
            <div style={{ marginTop: '16px', padding: '14px', background: '#f8fbff', borderRadius: '8px', border: '1px solid var(--line)' }}>
              <h3 className="field-label" style={{ margin: '0 0 6px', color: 'var(--navy)' }}>Estimate assumptions</h3>
              <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--muted)', fontSize: '10px', lineHeight: '1.6' }}>
                {quote.assumptions.map((assumption, idx) => (
                  <li key={idx}>{assumption}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="fine-print">A workshop must review and approve the proposal before the deposit can be paid.</p>
        </section>

        <aside className="panel payment-plan">
          <h2>Payment plan</h2>
          <div className="payment-amount">
            <span>Today · 50% deposit</span>
            <strong>{formatMoney(quote.deposit)}</strong>
            <small>Deposit required to start production.</small>
          </div>
          <div className="payment-amount balance-amount">
            <span>When finished · balance</span>
            <strong>{formatMoney(quote.balance)}</strong>
            <small>Remaining balance due upon delivery readiness.</small>
          </div>
          {isDemoMode && quote.paymentDemo ? (
            <Button variant="success" className="full" onClick={() => go('customer/tracking')}>View demo order <Icon name="arrow" size={15} /></Button>
          ) : (
            <Button variant="paypal" className="full" disabled={isConnectedMode || busy || !approved || isNeedsInfo} onClick={payDepositDemo}>
              {busy ? 'Updating…' : isConnectedMode ? 'PayPal checkout below' : approved ? `Simulate ${formatMoney(quote.deposit)} deposit` : isNeedsInfo ? 'Waiting for information' : 'Waiting for workshop approval'}
            </Button>
          )}
          {isConnectedMode && approved && order?.orderId && <PayPalCheckout orderId={order.orderId} type="deposit" refresh={refresh} />}
          {isDemoMode && <p className="secure-note">Simulation only. No PayPal transaction is created and no money is charged.</p>}
          {!order && (
            <Button variant="secondary" className="full approve-button" disabled={busy || approved || isNeedsInfo} onClick={approve}>
              {approved ? 'Approved' : isNeedsInfo ? 'Information needed' : 'Approve quote'}
            </Button>
          )}
        </aside>
      </div>
    </div>
  )
}

export default QuoteReviewPage
