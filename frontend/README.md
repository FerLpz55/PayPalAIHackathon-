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
- Speech input uses the browser Web Speech API when available. Unsupported browsers receive a text-input fallback.
- Receipt files are not uploaded or retained; the UI only records their names in local demo data.
- Use browser developer tools to clear the `tallerclaro.demo.v1` local storage key and restore the initial examples.

## Project structure

```text
src/
  App.jsx                 Routes, reusable UI, and screen components
  App.css                 Responsive styles and shared design tokens
  index.css               Document-level reset
  services/mockApi.js     Replaceable local demo service
docs/
  API_CONTRACT.md         Proposed backend handoff and data models
```

## Accessibility and responsive behavior

The interface uses semantic landmarks, labeled fields, visible focus styles, keyboard-operable controls, live status/error messages, reduced-motion handling, and a mobile navigation drawer. Layouts adapt at 760 px and 1100 px; short landscape viewports also collapse the workshop sidebar and use a two-column metric layout. The order table remains horizontally scrollable when its columns cannot fit.

## Backend handoff

The repository now includes a Python/FastAPI layered monolith foundation in
`../Backend/`, with only `GET /api/health` implemented. This frontend still uses
local mocks. See the [backend guide](../Backend/README.md) and
[architecture plan](../docs/superpowers/plans/2026-10-31-fastapi-layers.md).

Replace the functions in `src/services/mockApi.js` with the agreed API client. Keep server-side pricing and payment verification authoritative. The endpoint names in `docs/API_CONTRACT.md` are a proposal and require backend agreement. No backend, database, authentication system, AI provider, or PayPal SDK is included in this frontend.
