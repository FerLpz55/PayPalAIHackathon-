import { useEffect, useState } from 'react'
import AccountingAssistant from '../components/accounting/AccountingAssistant.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import Metric from '../components/ui/Metric.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import { apiClient, isConfigurationMissing } from '../services/apiClient.js'
import { formatMoney } from '../utils/format.js'

function AccountingPage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiClient.getFinancialSummary()
      .then((data) => {
        if (active) setSummary(data)
      })
      .catch((caught) => {
        if (!active) return
        setSummary(null)
        setError(
          caught?.status === 401 || caught?.status === 403
            ? 'The workshop session is not authorized to read accounting data.'
            : caught?.message || 'Accounting data could not be loaded from the backend.'
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  if (isConfigurationMissing) {
    return (
      <div className="page-content">
        <EmptyState
          title="Backend connection not configured"
          text="Accounting features are unavailable until VITE_API_BASE_URL is configured."
        />
      </div>
    )
  }

  return (
    <div className="page-content">
      <PageHeading
        title="Workshop Financials & Accounting"
        description="Real-time revenue, PayPal collections, and financial insights powered by AI."
      />
      
      {/* Asistente contable con IA */}
      <AccountingAssistant />

      {loading ? <LoadingState /> : error ? (
        <div className="panel" style={{ padding: 20 }}>
          <p role="alert" className="inline-error">{error}</p>
          <p className="status-help">No sample figures are shown as real accounting data. Retry after the backend session is available.</p>
        </div>
      ) : (
        <>
          <div className="section-head accounting-heading" style={{ marginTop: 24 }}>
            <div>
              <h2>Financial Overview</h2>
              <p>Aggregated metrics computed in PostgreSQL and verified via PayPal transactions.</p>
            </div>
          </div>

          <section className="metric-row accounting-metrics">
            <Metric label="Total Contracted" value={formatMoney(summary?.totalContracted ?? 0)} detail="All approved customer orders" />
            <Metric label="Collected via PayPal" value={formatMoney(summary?.collectedTotal ?? 0)} detail="Deposits and balances cleared" tone="green" />
            <Metric label="Pending Collection" value={formatMoney(summary?.pendingToCollect ?? 0)} detail="Awaiting delivery & balances" tone="blue" />
          </section>

          <div className="detail-grid" style={{ marginTop: 16 }}>
            <section className="panel detail-panel">
              <h2>Order Pipeline Metrics</h2>
              <p>Summary of active carpentry commissions:</p>
              <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Total orders placed</span>
                  <strong>{summary?.ordersCount ?? 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Active production</span>
                  <strong>{summary?.activeOrdersCount ?? summary?.ordersCount ?? 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Awaiting initial deposit</span>
                  <strong>{summary?.awaitingDeposit ?? 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Completed & delivered</span>
                  <strong style={{ color: 'var(--green)' }}>{summary?.deliveredOrdersCount ?? 0}</strong>
                </div>
              </div>
            </section>

            <section className="panel detail-panel">
              <h2>Cashflow Breakdown</h2>
              <p>Verified income segments:</p>
              <div style={{ display: 'grid', gap: 12, marginTop: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Collected advance deposits</span>
                  <strong style={{ color: 'var(--navy)' }}>{formatMoney(summary?.collectedDeposits ?? summary?.collectedTotal ?? 0)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Collected final balances</span>
                  <strong style={{ color: 'var(--green)' }}>{formatMoney(summary?.collectedBalances ?? 0)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                  <span>Average order value</span>
                  <strong>{formatMoney(summary?.averageOrderValue ?? 0)}</strong>
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  )
}

export default AccountingPage
