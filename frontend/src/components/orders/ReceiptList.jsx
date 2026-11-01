import { formatMoney } from '../../utils/format.js'

function ReceiptList({ receipts, showDetails = false }) {
  return receipts.map((receipt) => (
    <div className="mini-receipt" key={receipt.id}>
      {showDetails ? (
        <span><strong>{receipt.label}</strong><small>{receipt.id} · {receipt.date}</small></span>
      ) : (
        <span>{receipt.label}</span>
      )}
      {showDetails ? <b>{formatMoney(receipt.amount)}</b> : <strong>{formatMoney(receipt.amount)}</strong>}
    </div>
  ))
}

export default ReceiptList
