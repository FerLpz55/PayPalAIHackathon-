# TallerClaro Frontend

React frontend for carpentry project requests, quote review, order views, customer tracking, PayPal checkout, and workshop summaries. The checked-in application provides an explicit browser-only DEMO mode and a REAL mode that calls the configured FastAPI API. Source integration is not evidence of runtime availability.

## Current implementation status

| Area | Source status | Runtime status |
|---|---|---|
| Demo data and simulated flows | Implemented with mockApi and localStorage | Browser-only; no backend or PayPal charge |
| API client | Fetch client, adapters, error handling, demo/real/unconfigured mode guards | No deployed API was verified in the audit |
| Customer request/quote | Create/read/approve routes are called; generation errors and draft state are explicit | Partial: generation is workshop-protected; client clarification still lacks a customer-authorized contract |
| Workshop orders | Paginated list and PATCH calls exist | Page consumes limit/offset and renders page controls; API behavior was checked only with a local stub |
| Workshop order detail | GET by ID and PATCH are used | Detail/payment rendering was checked with a local stub, not FastAPI or PostgreSQL |
| Customer tracking/payment | Payment intent/status/capture paths exist | PayPal Sandbox and cross-session recovery not verified |
| Accounting summary/assistant | API calls exist | Summary failure is visible with unavailable values; real DB/AI responses remain unverified |
| Receipts/expenses | Demo filename preview only | No backend upload or expense ledger |
| Speech input | Browser Web Speech API when available | No transcription guarantee across browsers; not an AI quote service |

Frontend behavior has also been exercised in Chromium against local fixtures and HTTP stubs. Those checks do not establish compatibility with FastAPI, PostgreSQL, AI, Channel3, PayPal Sandbox, deployed CORS, or a hosted API. The historical documents under docs/API_CONTRACT.md and docs/DEMO_VS_REAL_FUNCTIONALITY.md contain superseded statements; check current backend routers and schemas.

## Requirements

- Node.js 24.x (from package.json engines).
- pnpm 12.14.0 (from packageManager and pnpm-lock.yaml).
- A browser with JavaScript enabled.
- Backend services are not required for DEMO. REAL mode requires a reachable FastAPI backend and its database/configuration.

## Install and run

From the repository root:

    cd frontend
    pnpm install --frozen-lockfile

Copy frontend/.env.example to frontend/.env and select exactly the mode you intend to use. For Windows PowerShell:

    Copy-Item .env.example .env

Run the Vite development server:

    pnpm run dev

Available package scripts, confirmed in package.json:

| Command | Purpose |
|---|---|
| pnpm run dev | Start Vite development server |
| pnpm run test | Run the Vitest suite once (non-watch mode) |
| pnpm run lint | Run ESLint |
| pnpm run build | Create a production build |
| pnpm run preview | Preview an existing Vite build |

No command above was run as part of this documentation update.

## Modes and frontend environment

| Variable | Required | Meaning |
|---|---|---|
| VITE_APP_MODE | Explicitly set to demo for DEMO; optional for REAL when API URL is present | demo selects mockApi. A non-demo value does not by itself configure the API. |
| VITE_API_BASE_URL | Required for REAL mode | Backend origin only, without /api suffix or trailing slash. |

Example mode settings without secrets:

    # Browser-only sample data
    VITE_APP_MODE=demo
    VITE_API_BASE_URL=

    # Connected mode
    VITE_APP_MODE=real
    VITE_API_BASE_URL=https://your-backend-origin

All VITE_* variables are included in public frontend assets. Never place database, PayPal, AI, or other private credentials in them. Vercel variables are applied at build time; redeploy after changes.

### DEMO

Set VITE_APP_MODE=demo and run pnpm run dev. The frontend uses sample workshop/customer/order data and localStorage key tallerclaro.demo.v1. Order edits and simulated payments remain in that browser. DEMO does not call PayPal and must not be used as a financial record. Receipt selection stores the filename only; it does not upload or retain file contents. Demo accounting and AI responses are illustrative.

### REAL

Set VITE_APP_MODE=real and VITE_API_BASE_URL to the backend origin. The API client calls the /api routes and does not silently fall back to demo data. If the URL is missing and DEMO is not explicitly selected, the app shows an unconfigured state.

REAL mode currently has important blockers:

- Workshop sign-in holds Basic credentials in page memory until logout, 401, or reload. This was verified against a local stub only; credentials remain readable to JavaScript on the page and the flow needs HTTPS outside loopback.
- The customer request flow calls workshop-protected quote generation. Errors are visible and an incomplete draft is not offered for approval; customer clarification still lacks an authorized customer contract.
- Customer tokens are stored in sessionStorage; no email delivery or cross-device recovery flow is included.
- The quote lookup query does not reliably hydrate the requested quote. The workshop quote lookup does not add Basic Auth.
- Workshop order detail calls the detail endpoint and renders returned payments; the wire flow was checked against a stub, not a real backend.
- PayPal recovery depends on the current browser session. If storage is lost, there is no API to list the customer's pending attempts.
- Accounting summary errors are shown as unavailable/error states rather than being represented as financial zeroes.
- Receipts and expense reports have no backend support.

Treat REAL mode as a local integration path, not a verified production customer experience. No PostgreSQL, deployed API, AI provider, Channel3, or PayPal Sandbox was contacted.

## Routes

The app uses hash routing in useHashRoute.js.

| Hash route | Screen |
|---|---|
| #/dashboard | Workshop dashboard |
| #/orders | Searchable/filterable workshop order list |
| #/quotes | Quote lookup and pending-order view |
| #/receipts | Demo-only receipt filename preview |
| #/accounting | Workshop summary and AI assistant |
| #/customer/new | Customer project request |
| #/customer/quote | Quote review, approval, and deposit checkout |
| #/customer/tracking | Order tracking and balance checkout |
| #/customer/payment/return | Backend payment verification/capture return |
| #/customer/payment/cancel | Cancellation return and checkout resume |
| #/order/{id} | Workshop order detail view |

The sidebar also uses a customer/request hash that falls through to the request screen.

## Data and API

Frontend transport is in src/services/http.js; mode selection and API operations are in src/services/apiClient.js; wire adapters are in src/services/adapters.js. Demo fixtures and mutations are in src/services/mockApi.js. Session/payment recovery storage is in src/services/sessionStore.js.

REAL mode uses these backend routes:

- Quotes: POST /api/quotes; GET /api/quotes/{id}; POST generate, approve, and reject.
- Orders: GET /api/orders; GET /api/orders/{id}; PATCH /api/orders/{id}.
- Payments: POST /api/orders/{id}/payments; GET /api/payments/{id}; POST /api/payments/{id}/capture.
- Accounting: GET /api/accounting/summary; POST /api/accounting/assistant.

The backend is authoritative for pricing and payment verification. The frontend never marks an order paid based only on the PayPal return URL.

## Testing

Frontend test files are under src/**/__tests__ and are intended to run with `pnpm run test`. In the November 9, 2026 local verification, Node 24.13.1 and pnpm 12.16.1 were available; pnpm commands could not acquire the global store lock in the restricted environment, and Vitest was absent from `node_modules`. Direct local ESLint and Vite build commands passed. There is no browser E2E script in package.json; the manual Chromium/stub evidence is documented in the phase reports and `docs/informes/INFORME_PRUEBAS_E2E.md`.

For REAL integration acceptance, separately verify the configured backend origin, CORS preflight, customer/workshop authorization, quote generation, order detail, PayPal Sandbox capture, and recovery behavior. No live service checks are implied by the local frontend tests.

## Vercel deployment

The checked-in frontend/vercel.json declares Vite, frozen-lockfile install, pnpm build, dist output, security headers, and immutable caching for hashed assets.

- Set Vercel Root Directory to frontend.
- Use Node 24.x and pnpm 12.14.0. ENABLE_EXPERIMENTAL_COREPACK=1 is documented for Vercel to honor packageManager.
- Set VITE_APP_MODE at build time.
- Set VITE_API_BASE_URL for REAL mode.
- Add the exact deployed frontend origin to backend TALLERCLARO_CORS_ORIGINS.
- Configure PayPal return/cancel URLs in backend to the HTTPS frontend routes.
- Preview deployments use distinct origins; only enable REAL mode there when CORS and credentials are deliberately configured.

## Related documentation

- Root project guide: ../README.md
- Backend guide: ../Backend/BACKENDREADME.md
- Database guide: ../database/README.md
- PayPal return URL setup: docs/PAYPAL_RETURN_URLS.md
- Repository instructions: ../AGENTS.md
