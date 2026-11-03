import { useState } from 'react'
import DataLine from '../components/ui/DataLine.jsx'
import DemoNotice from '../components/ui/DemoNotice.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import ProgressTrack from '../components/ui/ProgressTrack.jsx'
import Status from '../components/ui/Status.jsx'
import { apiClient } from '../services/apiClient.js'
import { formatMoney } from '../utils/format.js'

function ReceiptsPage({ orders, loading, mutate }) {
  const [selected, setSelected] = useState('TC-1048')
  const order = orders.find((item) => item.id === selected) || orders[0]

  const addFiles = async (event) => {
    const files = [...(event.target.files || [])]
    if (!files.length || !order) return
    for (const file of files) await mutate(() => apiClient.addReceipt(order.id, file), `${file.name} added to the demo receipt list.`)
    event.target.value = ''
  }

  return (
    <div className="page-content">
      <PageHeading title="Material receipt demo" description="Preview local receipt-name entries alongside sample orders." />
      <DemoNotice text="This page stores selected file names only. It does not upload or retain files, verify amounts, or create official financial documents." />
      <div className="toolbar">
        <label className="select-label">
          <span className="sr-only">Choose an order</span>
          <select value={order?.id || ''} onChange={(event) => setSelected(event.target.value)}>
            {orders.map((item) => <option key={item.id} value={item.id}>{item.id} · {item.project}</option>)}
          </select>
        </label>
        <span className="results-count">Files stay in this browser demo</span>
      </div>
      {loading ? <LoadingState /> : order && (
        <div className="receipt-layout">
          <section className="panel receipt-main">
            <div className="section-head">
              <div><h2>{order.project}</h2><p>{order.id} · {order.customer}</p></div>
              <Status value={order.status} />
            </div>
            <label className="upload-area">
              <input type="file" accept="image/png,image/jpeg,application/pdf" multiple onChange={addFiles} />
              <span className="upload-icon"><Icon name="upload" size={20} /></span>
              <strong>Select receipt files for the local demo list</strong>
              <small>JPG, PNG or PDF · Only the selected file names are stored</small>
              <span className="button button-secondary">Choose files</span>
            </label>
            <h3 className="list-label">Sample receipt entries <span>{order.receipts.length}</span></h3>
            {order.receipts.length ? (
              <div className="receipt-list">
                {order.receipts.map((receipt) => (
                  <div className="receipt-row" key={receipt.id}>
                    <span className={`receipt-check ${receipt.state}`}><Icon name={receipt.state === 'verified' ? 'check' : 'receipt'} size={15} /></span>
                    <div>
                      <strong>{receipt.label}</strong>
                      <small>{receipt.id} · {receipt.date} · Sample entry · Not uploaded or reviewed</small>
                    </div>
                    <b>{receipt.amount ? formatMoney(receipt.amount) : '—'}</b>
                    <span className="status status-sample">Sample</span>
                  </div>
                ))}
              </div>
            ) : <EmptyState title="No receipt entries" text="Select a file to add its name to this local demo order. The file itself is not uploaded." />}
          </section>
          <aside className="panel spending-panel">
            <h2>Spending overview</h2>
            <p>Compare sample receipt amounts with the simulated deposit.</p>
            <div className="info-callout">Illustrative totals only. Neither payments nor receipt amounts are verified.</div>
            <DataLine label="Simulated deposit" value={formatMoney(order.paid)} />
            <DataLine label="Sample receipt amounts" value={formatMoney(order.spent)} />
            <ProgressTrack value={order.spent} total={order.paid} label="Sample receipt amounts compared with simulated deposit" />
            <p className="fine-print">A future backend integration needs authorized file storage and a defined receipt review process. No official receipt or financial record is created here.</p>
          </aside>
        </div>
      )}
    </div>
  )
}

export default ReceiptsPage
