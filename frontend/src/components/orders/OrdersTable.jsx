import Button from '../ui/Button.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Status from '../ui/Status.jsx'
import { formatMoney } from '../../utils/format.js'

function OrdersTable({ orders, go }) {
  if (!orders.length) {
    return <EmptyState title="No orders yet" text="Create a quote to see its order here." action={<Button onClick={() => go('customer/new')}>Start an order</Button>} />
  }
  return (
    <div className="table-scroll" role="region" aria-label="Orders table. Scroll horizontally to see all columns." tabIndex={0}>
      <table>
        <caption className="sr-only">Workshop orders with customer, total, status, and next step.</caption>
        <thead>
          <tr><th scope="col">Order</th><th scope="col">Client</th><th scope="col">Total</th><th scope="col">Status</th><th scope="col">Next step</th></tr>
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
              <td><button type="button" className="table-action" onClick={() => go(`order/${order.id}`)}>{order.next}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default OrdersTable
