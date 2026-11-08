import Button from '../ui/Button.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Status from '../ui/Status.jsx'
import { formatMoney } from '../../utils/format.js'

function OrdersTable({ orders, go, emptyTitle = 'No orders yet', emptyText = 'Create a quote to see its order here.', emptyAction = true }) {
  if (!orders.length) {
    return <EmptyState title={emptyTitle} text={emptyText} action={emptyAction ? <Button onClick={() => go('customer/new')}>Start an order</Button> : undefined} />
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
              <td><button type="button" className="table-action" onClick={() => go(`order/${order.id}`)}>View order</button></td>
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
          <button type="button" className="mobile-order-action" onClick={() => go(`order/${order.id}`)}>View order details</button>
        </li>
      ))}
    </ul>
    </>
  )
}

export default OrdersTable
