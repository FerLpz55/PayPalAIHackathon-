# TallerClaro Frontend

Responsive React frontend for TallerClaro. DEMO uses local sample data; REAL mode calls the configured FastAPI backend. A successful frontend build does not establish backend or PayPal Sandbox availability.

## Current integration status

| Classification | Current frontend features |
| --- | --- |
| **REAL (source integrated; runtime unverified)** | Quote request/review, customer link recovery, order list/detail, PayPal payment create, explicit `sync`/`cancel` reconciliation, verified return handling, workshop cookie session with CSRF, and AI bookkeeping assistant when `VITE_API_BASE_URL` points to a working backend. |
| **DEMO (explicit opt-in)** | Customer request, sample quote, simulated payment, tracking, dashboard, order updates, receipt-name entries, interactive demo AI bookkeeping assistant, and accounting summaries. Select with `VITE_APP_MODE=demo`; no PayPal charge is made. |
| **UNCONFIGURED** | If no API URL is set and DEMO was not explicitly selected, sample data is hidden and the app explains how to configure a mode. |
| **PARTIAL** | Voice-to-text can use the browser Web Speech API where available. It only transcribes text into the request form; it does not call an AI quote service. |
| **NOT IMPLEMENTED** | Receipt upload and accounting reports backed by server data. |

The backend repository contains quote, order, and payment route handlers, but source presence does not establish that those routes are deployed, configured, or operational. PayPal return/cancel URLs are configurable on the backend and require HTTPS. See [the current backend guide](../Backend/BACKENDREADME.md) and [PayPal return URL requirements](docs/PAYPAL_RETURN_URLS.md). The [API inventory](docs/API_CONTRACT.md) and [feature matrix](docs/DEMO_VS_REAL_FUNCTIONALITY.md) are historical snapshots with superseded statements.

Workshop authentication now uses a revocable `HttpOnly` cookie session created by `POST /api/auth/login`. Mutating cookie-authenticated requests send `X-CSRF-Token` (stored in `sessionStorage` after login/session) plus an allowed `Origin`. HTTP Basic remains behind `TALLERCLARO_ENABLE_WORKSHOP_BASIC_AUTH=false` and the frontend no longer sends it. A workshop sign-in screen gates `#/dashboard`, `#/orders`, `#/quotes`, `#/receipts`, `#/accounting` and `#/order/*`; the customer screens stay public.

Customer links carry a token in the URL (`#/customer/quote?token=...`). The frontend adopts the token into `sessionStorage`, removes it from the URL, and calls `GET /api/customer/context` to recover the quote, order and payments. Only the workshop can reissue the link (`POST /api/quotes/{id}/customer-access`).

Payments are created with `POST /api/orders/{id}/payments`, reconciled explicitly with `POST /api/payments/{id}/sync` (capture only when PayPal reports `APPROVED`) and closed with `POST /api/payments/{id}/cancel`. The frontend no longer calls `/capture`. Orders expose `financial_status` (`unpaid`, `deposit_paid`, `paid`) in the orders table, order detail, tracking and quote review.

The REAL customer flow (customer token → quote → approval → deposit reconciliation) and the workshop cookie session flow have automated coverage; runtime integration with PostgreSQL, AI and PayPal Sandbox is still unverified. See [the E2E suite](#end-to-end-tests).

## Run locally

```bash
pnpm install
pnpm run dev
```

Copy `.env.example` to `.env`. Set `VITE_API_BASE_URL` to the backend origin for REAL mode. Set `VITE_APP_MODE=demo` only when you intentionally want browser-only sample data.

Open the local URL printed by Vite. The project requires Node.js and pnpm. To run tests, lint, and build for production:

```bash
pnpm run test
pnpm run lint
pnpm run build
pnpm run preview
```

### End-to-end tests

Playwright drives the built-in Vite dev server and mocks the backend at the HTTP layer, so it does not need PostgreSQL, AI or PayPal credentials:

```bash
pnpm exec playwright install chromium   # first run only
pnpm run test:e2e
```

`test:e2e` is separate from `pnpm run test` (Vitest). The suite covers a customer token link that approves a quote and reconciles a mocked PayPal deposit, and the workshop cookie-session gate plus sign out.

## Deploy on Vercel

The frontend is a static Vite build with hash routes, so no rewrite rules are needed. In Vercel, import the GitHub repository and set **Root Directory** to `frontend`. Install, build and output settings come from `vercel.json` (`pnpm install --frozen-lockfile`, `pnpm run build`, `dist`).

Versions are pinned in the repository: pnpm through `packageManager` in `package.json` plus the committed `pnpm-lock.yaml`, and Node.js through `engines.node`.

Environment variables (Settings > Environment Variables) are embedded at build time; redeploy after changing them:

| Variable | Value | Required |
| --- | --- | --- |
| `ENABLE_EXPERIMENTAL_COREPACK` | `1` | Yes. Makes Vercel use the exact pnpm version from `packageManager`; without it Vercel may pick an older pnpm that cannot read this lockfile. |
| `VITE_APP_MODE` | `demo` (no backend) or `real` | Yes |
| `VITE_API_BASE_URL` | `https://<backend-origin>` (origin only, without `/api` or a trailing slash) | Only in REAL mode |

**Only the frontend is deployed on Vercel.** The FastAPI backend and PostgreSQL run on their own origin (any HTTPS host); they are not part of the Vercel project and no serverless function wraps them.

For REAL mode the backend must allow the Vercel origin in `TALLERCLARO_CORS_ORIGINS` **with credentials** (`allow_credentials=True`), and PayPal return/cancel URLs must point to `https://<vercel-origin>/#/customer/payment/return` and `/#/customer/payment/cancel`. Preview deployments get different `*.vercel.app` origins; set `VITE_APP_MODE=demo` for the Preview environment unless those origins are added to CORS.

Because frontend and API are different sites, workshop session cookies need `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none` (requires HTTPS and a browser that accepts third-party cookies). With both on the same site, keep the default `lax`. The CSRF token is returned in the login/session body and stored in `sessionStorage`, so the backend domain must also expose `/api/auth/*` in CORS.

`vercel.json` applies security headers (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`) and long-term caching for hashed assets. Once the backend domain is fixed, narrow `connect-src` from `https:` to that origin. Never put secrets in `VITE_*` variables: they are public in the bundle.

## Screens and routes

The app uses hash routes so the current screen can be opened directly without a router dependency.

| Route | Screen |
| --- | --- |
| `#/dashboard` | Workshop summary and recent orders |
| `#/orders` | Searchable order list and status filter |
| `#/quotes` | Latest estimate and quotes awaiting approval |
| `#/receipts` | Local receipt-name entries and illustrative spending summary |
| `#/accounting` | Illustrative monthly income and expenses + AI bookkeeping assistant |
| `#/customer/new` | Customer project request |
| `#/customer/quote` | Quote review, approval, and PayPal deposit checkout (sample data in DEMO) |
| `#/customer/tracking` | Order progress, receipt entries, and balance payment (sample data in DEMO) |
| `#/customer/payment/return` | Customer PayPal return and backend capture verification |
| `#/customer/payment/cancel` | Customer PayPal cancellation review and checkout resume |
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
    auth/                 WorkshopLogin cookie-session sign-in form
    orders/               OrdersTable, ReceiptList
    customer/             RequestForm, HowItWorks, PayPalCheckout
    accounting/           AccountingAssistant
  pages/                  One file per workshop screen
    customer/             Customer screens (request, quote review, tracking, payment return)
  hooks/                  useDemoData, useHashRoute, useQuoteRequest, useSpeechInput, useAccountingAssistant, useWorkshopSession
    __tests__/            Vitest suites for quote title derivation
  services/
    apiClient.js          Facade preserving the public service interface
    http.js               Fetch transport with cookies/CSRF, mode detection, and ApiError
    adapters.js           API-to-UI normalization for quotes, orders, and accounting
    sessionStore.js       sessionStorage for workshop CSRF, customer tokens and payment recovery
    mockApi.js            Replaceable local demo service
    __tests__/            Vitest suites for adapters, transport, API client and session storage
  utils/                  formatMoney, shared constants, security, and analytics
    __tests__/            Vitest suites for URL safety
  styles/                 Global reset and application styles
e2e/
  critical-flows.spec.js  Playwright customer and workshop critical flows
docs/
  API_CONTRACT.md         Historical backend contract snapshot (see banner)
  DEMO_VS_REAL_FUNCTIONALITY.md Feature classifications and evidence
playwright.config.js      Playwright projects and Vite web server
```

## Accessibility and responsive behavior

The interface uses semantic landmarks, labeled fields, visible focus styles, keyboard-operable controls, live status/error messages, reduced-motion handling, and a mobile navigation drawer. Layouts adapt at 900 px and 1100 px; short landscape viewports also collapse the workshop sidebar and use a two-column metric layout. Order lists use an accessible table on larger screens and stacked order cards on narrow screens. See [the Issue #21 review](docs/ACCESSIBILITY_RESPONSIVE_REVIEW.md) for accessibility test coverage and limitations.

## Backend handoff

Keep demo operations isolated in `src/services/mockApi.js`. Do not silently fall back to demo data after a backend error. Keep server-side pricing and payment verification authoritative. Consult current routers and schemas rather than the historical contract for endpoint behavior; runtime availability has not been established. Database, AI and PayPal provider secrets, the workshop password hash and the customer-token secret belong only on the backend; the frontend holds no workshop credentials.
