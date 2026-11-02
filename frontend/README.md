# TallerClaro Frontend

Responsive React frontend for the PayPal AI Hackathon carpentry quote and order management project. The interface follows the connected Penpot design. All current business workflows are local demonstrations; the frontend has no backend-connected feature and must not be used with real customer or payment data.

## Current integration status

| Classification | Current frontend features |
| --- | --- |
| **REAL** | None of the customer, quote, order, payment, receipt, or accounting workflows is connected to a verified backend integration. |
| **DEMO** | Customer request submission, sample quote generation/review/approval, simulated payment, tracking, dashboard, order updates, receipt-name entries, and accounting summaries. They use fixed/sample data and local browser state. |
| **PARTIAL** | Voice-to-text can use the browser Web Speech API where available. It only transcribes text into the request form; it does not call an AI quote service. |
| **NOT IMPLEMENTED** | Frontend API client, backend authentication/session flow, customer tracking-token flow, and live AI, PayPal, order, receipt, or accounting integrations. |

The backend repository contains quote, order, and payment route handlers, but source presence does not establish that those routes are deployed, configured, or operational. The frontend does not call them. See [API contract and source status](docs/API_CONTRACT.md) and the [demo versus real feature matrix](docs/DEMO_VS_REAL_FUNCTIONALITY.md) for evidence and gaps.

## Run locally

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite. The project requires Node.js with npm. To create and inspect a production build:

```bash
npm run lint
npm run build
npm run preview
```

## Screens and routes

The app uses hash routes so the current screen can be opened directly without a router dependency.

| Route | Screen |
| --- | --- |
| `#/dashboard` | Workshop summary and recent orders |
| `#/orders` | Searchable order list and status filter |
| `#/quotes` | Latest estimate and quotes awaiting approval |
| `#/receipts` | Local receipt-name entries and illustrative spending summary |
| `#/accounting` | Illustrative monthly income and expenses |
| `#/customer/new` | Customer project request |
| `#/customer/quote` | Fixed sample cost breakdown and simulated approval/payment actions |
| `#/customer/tracking` | Local example progress, receipt entries, and simulated payment summary |
| `#/order/TC-1048` | Workshop order details and status editor |

## Demo behavior

- Seeded orders and the current quote are held by the frontend demo service. User changes are persisted to the `tallerclaro.demo.v1` local browser storage key; they are not sent to a server.
- Quote generation uses a fixed sample estimate; it does not call an AI service or calculate a real price.
- Quote approval and payment actions update local demo state only. The payment action is explicitly labeled as a simulation; no PayPal checkout or payment request is started and no charge is made.
- The customer request is text or voice only. Speech input uses the browser Web Speech API when available; unsupported browsers receive a text-input fallback.
- Selecting a receipt file stores its name only. The file is not uploaded or retained; receipt amounts and statuses are examples, not verified records or official financial documents.
- Accounting totals and monthly chart data are illustrative browser-side figures, not business records, verified payments, or tax reports.
- Clear the `tallerclaro.demo.v1` key using browser developer tools and reload to restore the seeded examples.
- Never enter real customer, payment, or financial data in this frontend demo.

## Project structure

The code follows a layer-based (type-based) structure: each folder groups files by their technical role.

```text
src/
  main.jsx                Entry point
  App.jsx                 Layout and hash routing only
  components/
    ui/                   Reusable building blocks (Button, Icon, Status, DataLine, ...)
    layout/               Sidebar, Topbar, CustomerHeader, Toast
    orders/               OrdersTable, ReceiptList
    customer/             RequestForm, HowItWorks
  pages/                  One file per workshop screen
    customer/             Customer screens (request, quote review, tracking)
  hooks/                  useDemoData, useHashRoute, useQuoteRequest, useSpeechInput
  services/mockApi.js     Replaceable local demo service
  utils/                  formatMoney and shared constants
  styles/                 Global reset and application styles
docs/
  API_CONTRACT.md         Backend source contract and frontend integration status
  DEMO_VS_REAL_FUNCTIONALITY.md Feature classifications and evidence
```

## Accessibility and responsive behavior

The interface uses semantic landmarks, labeled fields, visible focus styles, keyboard-operable controls, live status/error messages, reduced-motion handling, and a mobile navigation drawer. Layouts adapt at 900 px and 1100 px; short landscape viewports also collapse the workshop sidebar and use a two-column metric layout. Order lists use an accessible table on larger screens and stacked order cards on narrow screens. See [the Issue #21 review](docs/ACCESSIBILITY_RESPONSIVE_REVIEW.md) for accessibility test coverage and limitations.

## Backend handoff

Keep demo operations isolated in `src/services/mockApi.js`. Do not silently fall back to demo data after a backend error. A future API client must wait for the unresolved authentication, customer-token, CORS, error, runtime, and endpoint behavior questions in `docs/API_CONTRACT.md`. Keep server-side pricing and payment verification authoritative. The endpoint behavior in that document is verified from checked-in backend source only; runtime availability has not been established. No backend, database, authentication system, AI provider, or PayPal SDK is included in this frontend.
