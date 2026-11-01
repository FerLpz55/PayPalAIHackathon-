import Button from '../ui/Button.jsx'
import EmptyState from '../ui/EmptyState.jsx'
import Status from '../ui/Status.jsx'
import { formatMoney } from '../../utils/format.js'

function OrdersTable({ orders, go }) {
  if (!orders.length) {
    return <EmptyState title="No orders yet" text="Create a quote to see its order here." action={<Button onClick={() => go('customer/new')}>Start an order</Button>} />
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr><th>Order</th><th>Client</th><th>Total</th><th>Status</th><th>Next step</th></tr>
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
              <td><button className="table-action" onClick={() => go(`order/${order.id}`)}>{order.next}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default OrdersTable
