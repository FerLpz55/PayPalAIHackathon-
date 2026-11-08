import { useState } from 'react'
import AccountingAssistant from '../components/accounting/AccountingAssistant.jsx'
import Button from '../components/ui/Button.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import ProgressTrack from '../components/ui/ProgressTrack.jsx'
import { apiClient, isDemoMode, isConfigurationMissing } from '../services/apiClient.js'
import EmptyState from '../components/ui/EmptyState.jsx'
import { formatMoney } from '../utils/format.js'

function AccountingPage({ orders, loading, mutate }) {
  const [showFinish, setShowFinish] = useState(false)
  const ready = orders.find((order) => order.status === 'ready_to_finish' && !order.demoCompletionNoteAt)
  const completionNote = orders.find((order) => order.demoCompletionNoteAt)
  const received = orders.reduce((sum, order) => sum + order.paid, 0)
  const spent = orders.reduce((sum, order) => sum + order.spent, 0)
  const monthly = [
    { month: 'Jul', in: 7100, out: 3400 },
    { month: 'Aug', in: 8200, out: 4100 },
    { month: 'Sep', in: 7600, out: 3800 },
    { month: 'Oct', in: Math.max(received, 1000), out: Math.max(spent, 600) },
  ]
  const highest = Math.max(...monthly.map((item) => item.in))
  const expenses = [['Materials', Math.min(spent, 4200)], ['Workshop costs', Math.max(0, spent - 4200)], ['Other expenses', 0]]

  if (isConfigurationMissing) {
    return (
      <div className="page-content">
        <EmptyState
          title="Backend connection not configured"
          text="Accounting features are unavailable until VITE_API_BASE_URL is configured. No sample figures are being shown as real."
        />
      </div>
    )
  }

  const finish = async () => {
    if (!ready) return
    await mutate(() => apiClient.recordDemoCompletionNote(ready.id), 'Demo note saved locally. Production status and payment remain unchanged.')
    setShowFinish(false)
  }

  return (
    <div className="page-content">
      <PageHeading title="Illustrative workshop totals" description="Explore sample payment and expense summaries; these are not business financial records." />
      <AccountingAssistant />
      <DemoNotice text="The charts and totals below are demo data calculated in the browser. They are not verified payments, expenses, accounting records, or tax reports." />
      {isDemoMode && completionNote && <p className="info-callout" role="status" aria-live="polite">A local demo note was recorded for {completionNote.id}. Its production status and payment information were not changed.</p>}
      {isDemoMode && ready && (
        <section className="panel finish-banner">
          <div>
            <span className="success-kicker"><Icon name="check" size={14} /> Ready to finish</span>
            <h2>{ready.project}</h2>
            <p>{ready.id} · {ready.customer} · Simulated deposit {formatMoney(ready.paid)}</p>
            <small>This legacy sample status has no backend mapping. Record a local demo note only; no delivery or payment will be recorded.</small>
          </div>
          <Button variant="secondary" onClick={() => setShowFinish(true)}>Record demo note</Button>
        </section>
      )}
      {isDemoMode ? (
        <>
          <div className="section-head accounting-heading">
            <div><h2>Your month, made simple</h2><p>October 2026 · Illustrative demo figures</p></div>
          </div>
          {loading ? <LoadingState /> : (
            <>
              <section className="metric-row accounting-metrics">
                <Metric label="Simulated payments" value={formatMoney(received)} detail="Local demo amounts" tone="green" />
                <Metric label="Sample expenses" value={formatMoney(spent)} detail="Receipt amounts in demo data" />
                <Metric label="Illustrative remainder" value={formatMoney(received - spent)} detail="Demo amounts minus sample expenses" tone="green" />
              </section>
              <div className="accounting-grid">
                <section className="panel chart-panel">
                  <h3>Income and spending</h3>
                  <p>Sample monthly amounts for this demonstration.</p>
                  <div className="chart" role="img" aria-label="Sample income and spending comparison from July to October">
                    {monthly.map((month) => (
                      <div className="chart-month" key={month.month}>
                        <div className="bars">
                          <span className="bar income" style={{ height: `${Math.max(8, (month.in / highest) * 100)}%` }} title={`Received ${formatMoney(month.in)}`} />
                          <span className="bar expense" style={{ height: `${Math.max(8, (month.out / highest) * 100)}%` }} title={`Spent ${formatMoney(month.out)}`} />
                        </div>
                        <small>{month.month}</small>
                      </div>
                    ))}
                  </div>
                  <p className="sr-only">
                    Monthly values: {monthly.map((month) => `${month.month}: received ${formatMoney(month.in)}, spent ${formatMoney(month.out)}`).join('. ')}.
                  </p>
                  <div className="chart-legend"><span><i className="legend-income" /> Received</span><span><i className="legend-expense" /> Spent</span></div>
                </section>
                <section className="panel expense-panel">
                  <h3>Where it went</h3>
                  <p>Receipt amounts currently entered in the demo.</p>
                  {expenses.map(([label, amount]) => (
                    <div className="expense-item" key={label}>
                      <DataLine label={label} value={formatMoney(amount)} />
                      <ProgressTrack value={amount} total={spent} label={`${label} spending share`} />
                    </div>
                  ))}
                  <div className="info-callout">This demo does not connect to PayPal or move money. No verified payment information is shown.</div>
                </section>
              </div>
            </>
          )}
        </>
      ) : (
        <section className="panel" style={{ marginTop: '16px' }}>
          <EmptyState
            title="Monthly expense charts are demo only"
            text="Material costs and monthly expense breakdowns are not recorded in the server yet. The AI assistant above operates on verified PayPal order totals from the backend."
          />
        </section>
      )}
      {showFinish && (
        <ConfirmDialog
          title="Record a demo completion note?"
          text={`Save a local note for ${ready?.id}. The order's production status will remain Ready to finish. This does not record delivery or verify or collect payment.`}
          confirmLabel="Save demo note"
          onConfirm={finish}
          onClose={() => setShowFinish(false)}
        />
      )}
    </div>
  )
}

export default AccountingPage
