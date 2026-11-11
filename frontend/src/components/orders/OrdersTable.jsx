import { useState } from 'react'
import Button from '../ui/Button.jsx'
import ConfirmDialog from '../ui/ConfirmDialog.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Status from '../ui/Status.jsx'
import { apiClient } from '../../services/apiClient.js'
import { formatMoney } from '../../utils/format.js'

function OrdersTable({ orders, go, mutate, emptyTitle = 'No orders yet', emptyText = 'Create a quote to see its order here.', emptyAction = true }) {
  const [confirmState, setConfirmState] = useState(null)

  if (!orders.length) {
    return <EmptyState title={emptyTitle} text={emptyText} action={emptyAction ? <Button onClick={() => go('customer/new')}>Start an order</Button> : undefined} />
  }

  const handleConfirmAction = () => {
    if (!confirmState || !mutate) return
    const { type, order } = confirmState
    const targetId = order.orderId || order.id
    setConfirmState(null)
    if (type === 'cancel') {
      void mutate(() => apiClient.cancelOrder(targetId), `Order ${order.id} cancelled.`)
    } else if (type === 'delete') {
      void mutate(() => apiClient.deleteOrder(targetId), `Order ${order.id} deleted.`)
    }
  }

  return (
    <>
    <div className="table-scroll" role="region" aria-label="Orders table" tabIndex={0}>
      <table>
        <caption className="sr-only">Workshop orders with customer, total, status, and order details.</caption>
        <thead>
          <tr><th scope="col">Order</th><th scope="col">Client</th><th scope="col">Total</th><th scope="col">Status</th><th scope="col">Details</th></tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <tr key={order.id}>
              <td>
                <a href={`#/order/${order.id}`} className="order-id" onClick={(event) => { event.preventDefault(); go(`order/${order.id}`) }}>{order.id}</a>
                <span className="project-cell">{order.project}</span>
              </td>
              <td>{order.customer}</td>
              <td className="amount-cell">{formatMoney(order.amount)}</td>
              <td><Status value={order.status} /></td>
              <td>
                <div className="table-actions">
                  <button
                    type="button"
                    className="table-action"
                    aria-label={`View order ${order.id} for ${order.customer}`}
                    onClick={() => go(`order/${order.id}`)}
                  >
                    View order
                  </button>
                  {mutate && order.status !== 'cancelled' && order.status !== 'delivered' && (
                    <button
                      type="button"
                      className="table-action table-action-warn"
                      aria-label={`Cancel order ${order.id} for ${order.customer}`}
                      onClick={() => setConfirmState({ type: 'cancel', order })}
                    >
                      Cancel
                    </button>
                  )}
                  {mutate && (
                    <button
                      type="button"
                      className="table-action table-action-danger"
                      aria-label={`Delete order ${order.id} for ${order.customer}`}
                      onClick={() => setConfirmState({ type: 'delete', order })}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <ul className="mobile-order-list" aria-label="Orders">
      {orders.map((order) => (
        <li className="mobile-order-card" key={order.id}>
          <div className="mobile-order-heading">
            <div><a href={`#/order/${order.id}`} className="order-id" onClick={(event) => { event.preventDefault(); go(`order/${order.id}`) }}>{order.id}</a><span className="project-cell">{order.project}</span></div>
            <Status value={order.status} />
          </div>
          <dl className="mobile-order-meta">
            <div><dt>Customer</dt><dd>{order.customer}</dd></div>
            <div><dt>Order total</dt><dd>{formatMoney(order.amount)}</dd></div>
          </dl>
          <div className="table-actions" style={{ marginTop: 8 }}>
            <button
              type="button"
              className="mobile-order-action"
              aria-label={`View order details for ${order.id} (${order.customer})`}
              onClick={() => go(`order/${order.id}`)}
            >
              View order details
            </button>
            {mutate && order.status !== 'cancelled' && order.status !== 'delivered' && (
              <button
                type="button"
                className="table-action table-action-warn"
                aria-label={`Cancel order ${order.id} for ${order.customer}`}
                onClick={() => setConfirmState({ type: 'cancel', order })}
              >
                Cancel
              </button>
            )}
            {mutate && (
              <button
                type="button"
                className="table-action table-action-danger"
                aria-label={`Delete order ${order.id} for ${order.customer}`}
                onClick={() => setConfirmState({ type: 'delete', order })}
              >
                Delete
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
    {confirmState && (
      <ConfirmDialog
        title={confirmState.type === 'delete' ? 'Delete order?' : 'Cancel order?'}
        text={
          confirmState.type === 'delete'
            ? `Remove order ${confirmState.order.id} (${confirmState.order.customer}) from the workshop dashboard.`
            : `Cancel order ${confirmState.order.id} (${confirmState.order.customer}).`
        }
        confirmLabel={confirmState.type === 'delete' ? 'Delete order' : 'Cancel order'}
        onConfirm={handleConfirmAction}
        onClose={() => setConfirmState(null)}
      />
    )}
    </>
  )
}

export default OrdersTable
