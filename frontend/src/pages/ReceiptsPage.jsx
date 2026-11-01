import { useState } from 'react'
import DataLine from '../components/ui/DataLine.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import Icon from '../components/ui/Icon.jsx'
import LoadingState from '../components/ui/LoadingState.jsx'
import PageHeading from '../components/ui/PageHeading.jsx'
import ProgressTrack from '../components/ui/ProgressTrack.jsx'
import Status from '../components/ui/Status.jsx'
import SuccessCallout from '../components/ui/SuccessCallout.jsx'
import { mockApi } from '../services/mockApi.js'
import { formatMoney } from '../utils/format.js'

function ReceiptsPage({ orders, loading, mutate }) {
  const [selected, setSelected] = useState('TC-1048')
  const order = orders.find((item) => item.id === selected) || orders[0]

  const addFiles = async (event) => {
    const files = [...(event.target.files || [])]
    if (!files.length || !order) return
    for (const file of files) await mutate(() => mockApi.addReceipt(order.id, file), `${file.name} added to the demo receipt list.`)
    event.target.value = ''
  }

  return (
    <div className="page-content">
      <PageHeading title="Material receipts" description="Keep purchase records alongside the orders they support." />
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
              <strong>Drop receipt photos here, or browse files</strong>
              <small>JPG, PNG or PDF · Files are listed locally in this demo</small>
              <span className="button button-secondary">Choose receipts</span>
            </label>
            <h3 className="list-label">Uploaded receipts <span>{order.receipts.length}</span></h3>
            {order.receipts.length ? (
              <div className="receipt-list">
                {order.receipts.map((receipt) => (
                  <div className="receipt-row" key={receipt.id}>
                    <span className={`receipt-check ${receipt.state}`}><Icon name={receipt.state === 'verified' ? 'check' : 'receipt'} size={15} /></span>
                    <div>
                      <strong>{receipt.label}</strong>
                      <small>{receipt.id} · {receipt.date} · {receipt.state === 'verified' ? 'Sample status' : 'Awaiting backend review'}</small>
                    </div>
                    <b>{receipt.amount ? formatMoney(receipt.amount) : '—'}</b>
                    <Status value={receipt.state === 'verified' ? 'paid' : 'pending'} />
                  </div>
                ))}
              </div>
            ) : <EmptyState title="No receipts attached" text="Upload a photo or PDF to add it to this local demo order." />}
          </section>
          <aside className="panel spending-panel">
            <h2>Spending overview</h2>
            <p>Compare receipt entries with the advance.</p>
            <SuccessCallout title="Demo receipt summary" text="Amounts are not verified by an AI service." />
            <DataLine label="Advance received" value={formatMoney(order.paid)} />
            <DataLine label="Receipt amounts" value={formatMoney(order.spent)} />
            <ProgressTrack value={order.spent} total={order.paid} />
            <p className="fine-print">A connected backend must securely store uploaded files and verify each amount against the approved quote.</p>
          </aside>
        </div>
      )}
    </div>
  )
}

export default ReceiptsPage
