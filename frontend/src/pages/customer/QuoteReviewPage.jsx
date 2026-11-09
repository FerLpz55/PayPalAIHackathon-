import { useEffect, useRef, useState } from 'react'
import Button from '../../components/ui/Button.jsx'
import DataLine from '../../components/ui/DataLine.jsx'
import DemoNotice from '../../components/ui/DemoNotice.jsx'
import PayPalCheckout from '../../components/customer/PayPalCheckout.jsx'
import EmptyState from '../../components/ui/EmptyState.jsx'
import LoadingState from '../../components/ui/LoadingState.jsx'
import PageHeading from '../../components/ui/PageHeading.jsx'
import { apiClient, isConfigurationMissing, isDemoMode } from '../../services/apiClient.js'
import { isSafeExternalUrl } from '../../utils/security.js'
import { formatMoney } from '../../utils/format.js'

function QuoteReviewPage({ quote, orders, loading, go, mutate, refresh }) {
  const [busy, setBusy] = useState(false)
  const [additionalInfo, setAdditionalInfo] = useState('')
  const quoteId = quote?.numericId || quote?.id
  const [catalogState, setCatalogState] = useState(() => ({
    quoteId,
    search: '',
    loading: false,
    error: '',
    suggestions: quote?.suggestedProducts || [],
  }))
  const catalogRequestId = useRef(0)
  const catalogStateForQuote = String(catalogState.quoteId) === String(quoteId)
    ? catalogState
    : { quoteId, search: '', loading: false, error: '', suggestions: quote?.suggestedProducts || [] }
  const { search: catalogSearch, loading: searchLoading, error: catalogError, suggestions: activeSuggestions } = catalogStateForQuote

  useEffect(() => {
    catalogRequestId.current += 1
    return () => { catalogRequestId.current += 1 }
  }, [quoteId])

  const updateCatalogState = (patch) => {
    setCatalogState((current) => {
      const base = String(current.quoteId) === String(quoteId) ? current : catalogStateForQuote
      return { ...base, ...patch, quoteId }
    })
  }

  if (loading) return <div className="customer-page"><LoadingState /></div>
  if (isConfigurationMissing) return <div className="customer-page"><EmptyState title="Backend connection not configured" text="Quotes and payment actions are unavailable until VITE_API_BASE_URL is configured." /></div>
  if (!quote) {
    return <div className="customer-page"><EmptyState title="No quote is ready yet" text="Describe the piece you want made to prepare an estimate." action={<Button onClick={() => go('customer/new')}>Describe your project</Button>} /></div>
  }

  const approved = quote.status === 'approved'
  const isNeedsInfo = quote.status === 'needs_information'
  const isDraft = quote.status === 'draft'
  const isRejected = quote.status === 'rejected'
  const missingInfo = Array.isArray(quote.missing_info)
    ? quote.missing_info.filter((item) => typeof item === 'string' && item.trim())
    : []
  const statusLabel = {
    draft: 'Draft · not validated',
    needs_information: 'Information needed',
    pending_review: 'Ready for review',
    approved: 'Approved',
    rejected: 'Rejected',
  }[quote.status] || 'Status unavailable'
  const order = orders.find((item) => String(item.quoteId || item.id) === String(quote.numericId || quote.id))
  const items = quote.items || []
  const materials = items.filter((item) => item.kind === 'material')
  const labor = items.filter((item) => item.kind === 'labor')
  const otherItems = items.filter((item) => item.kind !== 'material' && item.kind !== 'labor')

  // Búsqueda en vivo de materiales en Channel3
  const searchCatalog = async (term) => {
    if (isDemoMode) {
      updateCatalogState({ error: 'Store search is unavailable in DEMO mode. No catalog request was sent.' })
      return
    }
    const normalizedTerm = term.trim()
    if (!normalizedTerm) return
    const requestId = ++catalogRequestId.current
    updateCatalogState({ loading: true, error: '' })
    try {
      const refreshed = await apiClient.getQuote(quoteId, { query: normalizedTerm })
      if (requestId !== catalogRequestId.current) return
      if (refreshed?.suggestedProducts?.length) {
        updateCatalogState({ suggestions: refreshed.suggestedProducts })
      } else {
        updateCatalogState({ suggestions: [], error: 'No products were returned for this search.' })
      }
    } catch (error) {
      if (requestId === catalogRequestId.current) updateCatalogState({ error: error?.message || 'The catalog could not be searched.' })
    } finally {
      if (requestId === catalogRequestId.current) updateCatalogState({ loading: false })
    }
  }

  const handleCatalogSearch = (e) => {
    e?.preventDefault()
    void searchCatalog(catalogSearch)
  }

  const applyProductToQuote = async (prod) => {
    const textToAdd = `Using ${prod.title} (priced at $${prod.priceUsd} from ${prod.source})`
    setBusy(true)
    await mutate(
      () => apiClient.submitMissingInfo(quote.numericId || quote.id, textToAdd),
      `Updated quote with ${prod.title}`
    )
    setBusy(false)
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
    const submitted = await mutate(
      () => apiClient.submitMissingInfo(quote.numericId || quote.id, additionalInfo.trim()),
      'Additional information submitted successfully.'
    )
    if (submitted !== false) setAdditionalInfo('')
    setBusy(false)
  }

  const reject = async () => {
    setBusy(true)
    await mutate(() => apiClient.rejectQuote(quote.numericId || quote.id), 'The quote was rejected/cancelled.')
    setBusy(false)
  }

  const retryGeneration = async () => {
    setBusy(true)
    await mutate(() => apiClient.retryQuoteGeneration(quote), 'The workshop returned an updated quote.')
    setBusy(false)
  }

  const measurementsText = `${quote.measurements?.width ?? '-'} wide · ${quote.measurements?.height ?? '-'} tall · ${quote.measurements?.depth ?? '-'} deep`

  return (
    <div className="customer-page">
      {isDemoMode && <DemoNotice text="Demo estimate only. It is not generated or validated by the workshop backend or an AI provider." />}
      <PageHeading title="Quote review" description={`Review the estimate for ${quote.customer}.`} />

      <div className="quote-review-grid">
        <section className="panel quote-breakdown">
          <div className="quote-title-row">
            <div>
              <h2>{quote.project}</h2>
              <p>{measurementsText}</p>
            </div>
            <span className={`status ${approved ? 'status-paid' : 'status-pending'}`}>
              {statusLabel}
            </span>
          </div>

          {isNeedsInfo && missingInfo.length > 0 && (
            <section className="status-help" aria-labelledby="quote-missing-info-heading" role="status" style={{ margin: '12px 0', padding: 14 }}>
              <h3 id="quote-missing-info-heading" className="field-label" style={{ margin: '0 0 8px' }}>Information requested by the workshop</h3>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {missingInfo.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
              </ul>
            </section>
          )}

          {/* Desglose de partidas */}
          <h3 className="field-label">Materials</h3>
          {materials.length > 0 ? (
            materials.map((item) => (
              <DataLine
                key={item.id || item.label}
                label={formatQuoteItem(item)}
                value={formatMoney(item.amount)}
              />
            ))
          ) : (
            <p className="status-help" style={{ margin: '4px 0 12px' }}>No material line items.</p>
          )}

          <h3 className="field-label labor-label">Workshop Labor</h3>
          {labor.length > 0 ? (
            labor.map((item) => (
              <DataLine
                key={item.id || item.label}
                label={formatQuoteItem(item)}
                value={formatMoney(item.amount)}
              />
            ))
          ) : (
            <p className="status-help" style={{ margin: '4px 0 12px' }}>No labor line items.</p>
          )}

          {otherItems.length > 0 && (
            <>
              <h3 className="field-label labor-label">Hardware, Finishes & Delivery</h3>
              {otherItems.map((item) => (
                <DataLine
                  key={item.id || item.label}
                  label={formatQuoteItem(item)}
                  value={formatMoney(item.amount)}
                />
              ))}
            </>
          )}

          <div className="quote-total"><span>{quote.total == null ? 'Total unavailable' : 'Estimated total'}</span><strong>{formatMoney(quote.total)}</strong></div>

          {/* PANEL DE PRODUCTOS SUGERIDOS Y BÚSQUEDA EN VIVO */}
          <div className="product-suggestions-section" style={{ marginTop: '24px', paddingTop: '18px', borderTop: '1px solid var(--line)' }}>
            <div className="section-head" style={{ marginBottom: 10 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Market Material References & Store Products</h3>
                <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 12 }}>
                  {isDemoMode ? 'Store pricing is not available in this local demo.' : 'Search the configured catalog for material references.'}
                </p>
              </div>
            </div>

            {/* Buscador en vivo de productos */}
            <form onSubmit={handleCatalogSearch} className="product-search-form" style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              <label htmlFor="catalog-search-input" className="sr-only">Search store catalog for lumber, hardware, or finishes</label>
              <input
                id="catalog-search-input"
                type="text"
                placeholder="Search lumber, hardware, finishes (e.g. solid oak, soft-close hinges)..."
                value={catalogSearch}
                onChange={(e) => updateCatalogState({ search: e.target.value })}
                style={{ flex: 1, minWidth: 220, padding: '0 12px', minHeight: 44, borderRadius: 8, border: '1px solid var(--line)', fontSize: 13 }}
              />
              <Button type="submit" variant="secondary" disabled={isDemoMode || searchLoading || !catalogSearch.trim()}>
                {searchLoading ? 'Searching…' : 'Search Store Catalog'}
              </Button>
            </form>

            {/* Chips de búsqueda rápida */}
            <div className="product-chips" style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
              {['Solid Oak Lumber', 'Pine Board', 'Soft Close Hinges', 'Drawer Slides', 'Polyurethane Varnish', 'Walnut Slab'].map((term) => (
                <button
                  key={term}
                  type="button"
                  className="assistant-chip"
                  disabled={isDemoMode || searchLoading}
                  onClick={() => {
                    updateCatalogState({ search: term, error: '' })
                    void searchCatalog(term)
                  }}
                >
                  {term}
                </button>
              ))}
            </div>

            {/* Grid de productos sugeridos */}
            <div aria-live="polite">
            {catalogError && <p className="inline-error" role="alert">{catalogError}</p>}
            {activeSuggestions.length > 0 ? (
              <div className="product-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                {activeSuggestions.map((prod, idx) => (
                  <div key={prod.id || idx} className="product-card" style={{ padding: 12, border: '1px solid var(--line)', borderRadius: 10, background: '#fff', display: 'flex', flexDirection: 'column' }}>
                    {prod.imageUrl ? (
                      <img src={prod.imageUrl} alt={prod.title} style={{ width: '100%', height: 110, objectFit: 'cover', borderRadius: 6, marginBottom: 8 }} />
                    ) : (
                      <div aria-hidden="true" style={{ width: '100%', height: 110, borderRadius: 6, background: 'var(--soft-blue)', display: 'grid', placeItems: 'center', color: 'var(--navy)', marginBottom: 8, fontSize: 13, fontWeight: 600 }}>
                        {prod.source || 'Store Item'}
                      </div>
                    )}
                    <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--blue)', marginBottom: 4 }}>
                      {prod.source || 'Retail Merchant'}
                    </span>
                    <strong style={{ fontSize: 12, lineHeight: 1.35, color: 'var(--text)', marginBottom: 6, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {prod.title}
                    </strong>
                    <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--navy)' }}>
                        {prod.priceUsd == null ? 'Price unavailable' : `$${Number(prod.priceUsd).toFixed(2)} USD`}
                      </span>
                      {prod.url && isSafeExternalUrl(prod.url) && (
                        <a
                          href={prod.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          aria-label={`Store ↗ — View ${prod.title} at ${prod.source || 'merchant'} (opens in new tab)`}
                          style={{ fontSize: 12, color: 'var(--blue)', textDecoration: 'none', minHeight: 28, display: 'inline-flex', alignItems: 'center' }}
                        >
                          Store ↗
                        </a>
                      )}
                    </div>
                    <Button
                      variant="subtle"
                      aria-label={`+ Apply to Quote: ${prod.title}`}
                      style={{ minHeight: 44, fontSize: 12, padding: '0 10px' }}
                      disabled={busy || prod.priceUsd == null}
                      onClick={() => applyProductToQuote(prod)}
                    >
                      + Apply to Quote
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="status-help">{isDemoMode ? 'No catalog results are included in this local demo.' : 'No products were returned. Search again or try a different material.'}</p>
            )}
            </div>
          </div>

          {/* Supuestos */}
          {quote.assumptions && quote.assumptions.length > 0 && (
            <div style={{ marginTop: '20px', padding: '14px', background: '#f8fbff', borderRadius: '8px', border: '1px solid var(--line)' }}>
              <h3 className="field-label" style={{ margin: '0 0 6px', color: 'var(--navy)' }}>Estimate specifications & assumptions</h3>
              <ul style={{ margin: 0, paddingLeft: '18px', color: 'var(--muted)', fontSize: 12, lineHeight: '1.6' }}>
                {quote.assumptions.map((assumption, idx) => (
                  <li key={idx}>{assumption}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Formulario de refinamiento / información adicional */}
          <div style={{ marginTop: '20px', padding: '16px', background: '#fff', borderRadius: '8px', border: '1px solid var(--line)' }}>
            <h3 style={{ margin: '0 0 6px', fontSize: 14, fontWeight: 600 }}>Customize or Refine Estimate</h3>
            <p style={{ margin: '0 0 10px', fontSize: 12, color: 'var(--muted)' }}>
              {isDemoMode ? 'Estimate refinement is unavailable in this local demo.' : 'Need different wood, extra shelves, or custom hardware? Add details for the workshop to review:'}
            </p>
            <form onSubmit={handleMissingInfoSubmit}>
              <label htmlFor="refine-estimate-textarea" className="sr-only">Additional project details to recalculate estimate</label>
              <textarea
                id="refine-estimate-textarea"
                rows="2"
                value={additionalInfo}
                onChange={(e) => setAdditionalInfo(e.target.value)}
                placeholder="e.g. Change wood to solid walnut and add soft-close hinges..."
                disabled={busy || isDemoMode}
                style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--line)', marginBottom: '10px', fontSize: 13 }}
              />
              <Button type="submit" variant="secondary" disabled={busy || !additionalInfo.trim()}>
                {busy ? 'Submitting…' : isDemoMode ? 'Refinement unavailable in DEMO' : 'Send additional details'}
              </Button>
            </form>
          </div>
        </section>

        {/* Panel lateral de pago / aprobación */}
        <aside className="panel payment-plan">
          <h2>Payment schedule</h2>
          <div className="payment-amount">
            <span>Advance deposit</span>
            <strong>{formatMoney(quote.deposit)}</strong>
            <small>Locks in workshop materials and scheduling.</small>
          </div>
          <div className="payment-amount balance-amount">
            <span>Remaining balance</span>
            <strong>{formatMoney(quote.balance)}</strong>
            <small>Due upon workshop completion before delivery.</small>
          </div>

          {isDraft && !isDemoMode && (
            <p className="status-help" role="status">This request is still a draft. It cannot be approved until the workshop generates and validates the estimate.</p>
          )}

          {quote.generationError && (
            <div className="inline-error" role="alert">
              <p>{quote.generationError}</p>
              {quote.status === 'draft' && !isDemoMode && (
                <Button variant="secondary" disabled={busy} onClick={retryGeneration}>
                  {busy ? 'Retrying generation…' : 'Retry quote generation'}
                </Button>
              )}
            </div>
          )}

          {isNeedsInfo && (
            <p className="status-help" role="status">The workshop needs more information before this quote can be reviewed.</p>
          )}

          {isDemoMode && isDraft && (
            <p className="status-help" role="status">This action only advances the local demo. It does not approve a real quote or start a payment.</p>
          )}

          {!approved && !isRejected && (quote.status === 'pending_review' || isDemoMode && isDraft) && (
            <div style={{ display: 'grid', gap: 10 }}>
              <Button variant={isDemoMode ? 'secondary' : 'paypal'} className="full approve-button" disabled={busy || quote.total == null || items.length === 0} onClick={approve}>
                {busy ? 'Processing approval…' : isDemoMode ? 'Simulate demo approval' : 'Approve quote'}
              </Button>
              <Button variant="subtle" className="full" disabled={busy} onClick={reject} style={{ color: '#aa3737' }}>
                Reject / Cancel Quote
              </Button>
            </div>
          )}

          {isRejected && (
            <div style={{ padding: 14, borderRadius: 8, background: '#fdf2f2', border: '1px solid #f9d6d6', textAlign: 'center' }}>
              <strong style={{ color: '#aa3737', display: 'block', marginBottom: 4 }}>Quote Cancelled</strong>
              <small style={{ color: 'var(--muted)' }}>This quote was cancelled and cannot be approved.</small>
            </div>
          )}

          {approved && !isDemoMode && order?.orderId && (
            <PayPalCheckout orderId={order.orderId} type="deposit" refresh={refresh} />
          )}

          {approved && isDemoMode && (
            <p className="status-help" role="status">The demo approval created a sample order. Payment is not available in DEMO mode.</p>
          )}

          {approved && !isDemoMode && !order && (
            <p className="status-help" style={{ textAlign: 'center' }}>Creating order details…</p>
          )}
        </aside>
      </div>
    </div>
  )
}

function formatQuoteItem(item) {
  const label = item.label || 'Unspecified item'
  const quantity = item.quantity != null && item.unit ? `${item.quantity} ${item.unit}` : null
  const unitAmount = item.unitAmount != null && Number.isFinite(Number(item.unitAmount))
    ? `@ ${formatMoney(item.unitAmount)}`
    : null
  const details = [quantity, unitAmount].filter(Boolean).join(' ')
  return details ? `${label} (${details})` : label
}

export default QuoteReviewPage
