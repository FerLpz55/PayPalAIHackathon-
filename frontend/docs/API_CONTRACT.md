# Frontend API Contract

## Current backend status

The backend is a Python/FastAPI layered monolith foundation. Its only implemented
endpoint is `GET /api/health`, returning `200 {"status":"ok"}`. The frontend is
not connected to it. The [backend plan](../../docs/superpowers/plans/2026-10-31-fastapi-layers.md)
defines architecture and delivery scope; the endpoints and models below remain
proposals for future business use cases.

The frontend currently uses `src/services/mockApi.js`. Replace that module with an HTTP implementation while keeping the view-facing methods stable. The mock writes local demo data to `localStorage`; it does not verify prices, receipts, order permissions, or PayPal transactions.

## Suggested endpoints

| Method | Endpoint | Frontend operation | Expected result |
| --- | --- | --- | --- |
| `GET` | `/api/orders` | `listOrders()` | `{ orders: Order[] }` |
| `GET` | `/api/quotes/:quoteId` | `getQuote()` | `Quote` |
| `POST` | `/api/quotes` | `createQuote(input)` | `Quote` with a server-generated ID and validated estimate |
| `POST` | `/api/quotes/:quoteId/approve` | `approveQuote()` | Approved `Quote`, or a validation error |
| `POST` | `/api/orders/:orderId/payments` | `simulatePayment(kind)` | Server-created payment session/intent; never mark paid from a client redirect |
| `PATCH` | `/api/orders/:orderId` | `updateStatus(id, status)` | Updated `Order`; authorized server-side |
| `POST` | `/api/orders/:orderId/receipts` | `addReceipt(id, file)` | Uploaded receipt metadata and review state |

Endpoint names are proposed handoff contracts, not an existing backend API. Confirm them with the backend team before implementation.

## Data models

```ts
type OrderStatus = 'pending' | 'paid' | 'in_progress' | 'delivered'
  | 'quote_sent' | 'ready_to_finish'

type QuoteLineItem = {
  id: string
  description: string
  quantity: number
  unit: string
  unitAmount: number
  amount: number
  category: 'material' | 'labor' | 'other'
}

type Quote = {
  id: string
  customerId?: string
  customerName: string
  customerEmail: string
  description: string
  items: QuoteLineItem[]
  currency: string
  total: number
  depositAmount: number
  balanceAmount: number
  status: 'draft' | 'needs_information' | 'pending_review' | 'approved' | 'rejected'
  assumptions?: string[]
  createdAt: string
}

type Order = {
  id: string
  quoteId: string
  customerName: string
  projectDescription: string
  total: number
  currency: string
  status: OrderStatus
  paymentStatus: 'unpaid' | 'partially_paid' | 'paid' | 'refunded' | 'failed'
  createdAt: string
  receipts: Receipt[]
}

type Receipt = {
  id: string
  orderId: string
  fileName: string
  amount?: number
  currency?: string
  reviewStatus: 'pending' | 'verified' | 'rejected'
  createdAt: string
}
```

## Integration requirements

- Price totals, deposit amounts, and balances are authoritative only when returned or verified by the server.
- Keep payment state separate from fulfillment status. A success/cancel URL is not proof of payment.
- Verify PayPal webhooks or server-side capture results before setting an order's payment status to paid.
- Protect workshop order updates with the authentication/authorization approach selected by the backend team.
- Validate and limit receipt uploads on the server. Store files outside browser local storage.
- Return structured errors such as `{ code, message, fieldErrors? }`; the UI should expose a useful recovery message without leaking secrets.
- Configure the frontend API base URL through a public client environment variable such as `VITE_API_BASE_URL`. Never put API secrets in `VITE_*` values.
- Define the application currency, tax treatment, estimate expiry, deposit policy, and exchange/rounding rules before enabling payment.
