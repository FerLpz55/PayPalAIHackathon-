import { useCallback, useEffect, useRef, useState } from 'react'
import Button from '../ui/Button.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import LoadingState from '../ui/LoadingState.jsx'
import { apiClient, QUOTE_INBOX_STATUSES } from '../../services/apiClient.js'
import { formatMoney } from '../../utils/format.js'

const QUOTE_STATUS_LABELS = {
  draft: 'New request',
  needs_information: 'Needs information',
  pending_review: 'Sent to customer',
  approved: 'Approved',
  rejected: 'Rejected',
}

const QUOTE_STATUS_CLASS = {
  draft: 'status-pending',
  needs_information: 'status-pending',
  pending_review: 'status-in_progress',
  approved: 'status-paid',
  rejected: 'status-cancelled',
}

const FILTERS = [
  { id: 'open', label: 'Open requests', statuses: QUOTE_INBOX_STATUSES },
  { id: 'all', label: 'All quotes', statuses: null },
]

function QuoteInbox({ onGenerated }) {
  const [filter, setFilter] = useState('open')
  const [state, setState] = useState({ loading: true, error: '', quotes: [], total: 0 })
  const [busyId, setBusyId] = useState(null)
  const [rowErrors, setRowErrors] = useState({})
  const [notes, setNotes] = useState({})
  const requestSeq = useRef(0)

  const load = useCallback(async () => {
    const requestId = ++requestSeq.current
    setState((current) => ({ ...current, loading: true, error: '' }))
    try {
      const statuses = FILTERS.find((item) => item.id === filter)?.statuses
      const page = await apiClient.listQuotes({ statuses })
      if (requestId === requestSeq.current) setState({ loading: false, error: '', quotes: page.quotes, total: page.total })
    } catch (error) {
      if (requestId === requestSeq.current) {
        setState({ loading: false, error: error?.message || 'The quote inbox could not be loaded.', quotes: [], total: 0 })
      }
    }
  }, [filter])

  useEffect(() => {
    const timer = window.setTimeout(() => { void load() }, 0)
    return () => window.clearTimeout(timer)
  }, [load])

  const generate = async (quote) => {
    setBusyId(quote.numericId)
    setRowErrors((current) => ({ ...current, [quote.numericId]: '' }))
    try {
      await apiClient.generateQuote(quote.numericId, notes[quote.numericId])
      setNotes((current) => ({ ...current, [quote.numericId]: '' }))
      await load()
      onGenerated?.(quote)
    } catch (error) {
      setRowErrors((current) => ({ ...current, [quote.numericId]: error?.message || 'The AI quote could not be generated.' }))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section aria-labelledby="quote-inbox-heading">
      <div className="section-head">
        <div>
          <h2 id="quote-inbox-heading">Customer requests</h2>
          <p>New requests arrive here. Generate the AI quote and it is sent to the customer for approval.</p>
        </div>
        <div className="table-actions" role="group" aria-label="Filter quotes">
          {FILTERS.map((item) => (
            <Button
              key={item.id}
              variant={filter === item.id ? 'primary' : 'secondary'}
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
            </Button>
          ))}
          <Button variant="subtle" onClick={() => void load()} disabled={state.loading}>Refresh</Button>
        </div>
      </div>

      <div className="panel table-panel">
        {state.loading ? <LoadingState /> : state.error ? (
          <p className="inline-error" role="alert" style={{ padding: 18 }}>{state.error}</p>
        ) : !state.quotes.length ? (
          <EmptyState title="No open requests" text="When a customer describes a piece, the request appears here." />
        ) : (
          <div className="table-scroll" role="region" aria-label="Customer requests" tabIndex={0}>
            <table>
              <caption className="sr-only">Customer quote requests with status, total and AI generation action.</caption>
              <thead>
                <tr><th scope="col">Request</th><th scope="col">Customer</th><th scope="col">Total</th><th scope="col">Status</th><th scope="col">Action</th></tr>
              </thead>
              <tbody>
                {state.quotes.map((quote) => {
                  const canGenerate = ['draft', 'needs_information'].includes(quote.status)
                  const missing = quote.missing_info || []
                  return (
                    <tr key={quote.numericId}>
                      <td style={{ maxWidth: 340 }}>
                        <span className="order-id">{quote.id}</span>
                        <span className="project-cell" title={quote.request} style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{quote.request}</span>
                        {quote.status === 'needs_information' && missing.length > 0 && (
                          <ul className="status-help" style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                            {missing.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                          </ul>
                        )}
                      </td>
                      <td>{quote.customer}<span className="project-cell">{quote.email}</span></td>
                      <td className="amount-cell">{quote.total == null ? '—' : formatMoney(quote.total)}</td>
                      <td><span className={`status ${QUOTE_STATUS_CLASS[quote.status] || 'status-pending'}`}>{QUOTE_STATUS_LABELS[quote.status] || quote.status}</span></td>
                      <td>
                        {canGenerate ? (
                          <div style={{ display: 'grid', gap: 6, minWidth: 170 }}>
                            {quote.status === 'needs_information' && (
                              <>
                                <label htmlFor={`quote-note-${quote.numericId}`} className="sr-only">Details for quote {quote.id}</label>
                                <input
                                  id={`quote-note-${quote.numericId}`}
                                  type="text"
                                  placeholder="Add the missing details…"
                                  value={notes[quote.numericId] || ''}
                                  onChange={(event) => setNotes((current) => ({ ...current, [quote.numericId]: event.target.value }))}
                                  style={{ minHeight: 40, padding: '0 10px', borderRadius: 8, border: '1px solid var(--line)', fontSize: 13 }}
                                />
                              </>
                            )}
                            <Button disabled={busyId != null} onClick={() => void generate(quote)} style={{ whiteSpace: 'nowrap' }}>
                              {busyId === quote.numericId ? 'Generating…' : quote.status === 'draft' ? 'Generate with AI' : 'Regenerate with AI'}
                            </Button>
                            {rowErrors[quote.numericId] && <span role="alert" className="inline-error">{rowErrors[quote.numericId]}</span>}
                          </div>
                        ) : (
                          <span className="status-help">{quote.status === 'pending_review' ? 'Awaiting customer approval' : '—'}</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

export default QuoteInbox
