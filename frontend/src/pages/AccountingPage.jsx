import { useState } from 'react'
import Button from '../components/ui/Button.jsx'
import ConfirmDialog from '../components/ui/ConfirmDialog.jsx'
import DataLine from '../components/ui/DataLine.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import ProgressTrack from '../components/ui/ProgressTrack.jsx'
import { mockApi } from '../services/mockApi.js'
import { formatMoney } from '../utils/format.js'

function AccountingPage({ orders, loading, mutate }) {
  const [showFinish, setShowFinish] = useState(false)
  const ready = orders.find((order) => order.status === 'ready_to_finish')
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

  const finish = async () => {
    if (!ready) return
    await mutate(() => mockApi.updateStatus(ready.id, 'delivered'), 'Order marked delivered in demo data. No payment was charged.')
    setShowFinish(false)
  }

  return (
    <div className="page-content">
      <PageHeading title="Finish the work. See what you earned." description="Track demo payments and workshop expenses in one place." />
      {ready && (
        <section className="panel finish-banner">
          <div>
            <span className="success-kicker"><Icon name="check" size={14} /> Ready to finish</span>
            <h2>{ready.project}</h2>
            <p>{ready.id} · {ready.customer} · Advance paid {formatMoney(ready.paid)}</p>
            <small>Mark the work complete to update its demo status. Final payment is not processed here.</small>
          </div>
          <Button variant="success" onClick={() => setShowFinish(true)}>Mark as finished</Button>
        </section>
      )}
      <div className="section-head accounting-heading">
        <div><h2>Your month, made simple</h2><p>October 2026 · Illustrative demo figures</p></div>
      </div>
      {loading ? <LoadingState /> : (
        <>
          <section className="metric-row accounting-metrics">
            <Metric label="Money received" value={formatMoney(received)} detail="Customer payments" tone="green" />
            <Metric label="Money spent" value={formatMoney(spent)} detail="Uploaded receipt amounts" />
            <Metric label="Remaining" value={formatMoney(received - spent)} detail="Received minus entered expenses" tone="green" />
          </section>
          <div className="accounting-grid">
            <section className="panel chart-panel">
              <h3>Income and spending</h3>
              <p>Sample monthly amounts for this demonstration.</p>
              <div className="chart" role="img" aria-label="Illustrative income and spending comparison from July to October">
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
              <div className="chart-legend"><span><i className="legend-income" /> Received</span><span><i className="legend-expense" /> Spent</span></div>
            </section>
            <section className="panel expense-panel">
              <h3>Where it went</h3>
              <p>Receipt amounts currently entered in the demo.</p>
              {expenses.map(([label, amount]) => (
                <div className="expense-item" key={label}>
                  <DataLine label={label} value={formatMoney(amount)} />
                  <ProgressTrack value={amount} total={spent} />
                </div>
              ))}
              <div className="info-callout">Your money stays in your PayPal account. No live payment information is shown in this demo.</div>
            </section>
          </div>
        </>
      )}
      {showFinish && (
        <ConfirmDialog
          title="Mark this order as finished?"
          text="This updates the sample order status in your browser. It will not send an invoice or charge the customer."
          confirmLabel="Mark as finished"
          onConfirm={finish}
          onClose={() => setShowFinish(false)}
        />
      )}
    </div>
  )
}

export default AccountingPage
