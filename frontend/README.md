# TallerClaro Frontend

Responsive React frontend for the PayPal AI Hackathon carpentry quote and order management project. The interface follows the connected Penpot file and keeps every unsupported integration visibly in demo mode.

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
| `#/receipts` | Receipt uploads and spending summary |
| `#/accounting` | Illustrative monthly income and expenses |
| `#/customer/new` | Customer project request |
| `#/customer/quote` | Cost breakdown and 50% deposit example |
| `#/customer/tracking` | Order progress, receipt list, and payment summary |
| `#/order/TC-1048` | Workshop order details and status editor |

## Demo behavior

- Sample orders, illustrative totals, and user-entered receipt file names are stored in local browser storage.
- Quote generation uses a fixed sample estimate; it does not call an AI service or calculate a real price.
- The “Approve example quote” and “Pay with PayPal” journey updates local demo state only. No payment request is sent and no charge is made.
- The customer request is text or voice only. Speech input uses the browser Web Speech API when available; unsupported browsers receive a text-input fallback.
- Receipt files are not uploaded or retained; the UI only records their names in local demo data.
- Use browser developer tools to clear the `tallerclaro.demo.v1` local storage key and restore the initial examples.

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
  API_CONTRACT.md         Proposed backend handoff and data models
```

## Accessibility and responsive behavior

The interface uses semantic landmarks, labeled fields, visible focus styles, keyboard-operable controls, live status/error messages, reduced-motion handling, and a mobile navigation drawer. Layouts adapt at 760 px and 1100 px; short landscape viewports also collapse the workshop sidebar and use a two-column metric layout. The order table remains horizontally scrollable when its columns cannot fit.

## Backend handoff

Replace the functions in `src/services/mockApi.js` with the agreed API client. Keep server-side pricing and payment verification authoritative. The endpoint names in `docs/API_CONTRACT.md` are a proposal and require backend agreement. No backend, database, authentication system, AI provider, or PayPal SDK is included in this frontend.
