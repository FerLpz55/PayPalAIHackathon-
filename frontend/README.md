# TallerClaro Frontend

React 19 + Vite frontend for carpentry project requests, quote review, workshop orders, customer tracking, PayPal checkout, and accounting summaries. It has three explicit states: browser-only DEMO, REAL connected to the FastAPI API, and UNCONFIGURED. Backend errors never fall back silently to demo data.

## Current implementation status

| Classification | Current frontend features |
| --- | --- |
| **REAL** | Quote request/review, customer-link recovery, paginated workshop quote/order views, PayPal payment creation and explicit `sync`/`cancel`, workshop cookie session with CSRF, and the accounting assistant. |
| **DEMO** | Sample customer, quote, order, tracking, simulated payment, dashboard, receipt-name, assistant, and accounting flows stored in the browser. No PayPal charge is made. |
| **UNCONFIGURED** | If no API URL is set and demo was not selected, sample data stays hidden and the UI explains how to configure a mode. |
| **PARTIAL** | Voice-to-text uses the browser Web Speech API where available; it only transcribes into the request form. |
| **NOT IMPLEMENTED** | Receipt upload and accounting reports backed by server data. |

Workshop authentication uses a revocable `HttpOnly` cookie created by `POST /api/auth/login`. Mutating workshop requests include `X-CSRF-Token`, obtained from login/session and stored in `sessionStorage`, plus an allowed `Origin`. The frontend does not send HTTP Basic credentials.

Customer links contain `?token=...`. The frontend adopts the token into `sessionStorage`, cleans it from the URL, and calls `GET /api/customer/context` to recover the quote, order, and payments. Only the workshop can reissue a link.

Payments are created with `POST /api/orders/{id}/payments`, reconciled with `POST /api/payments/{id}/sync`, and closed with `POST /api/payments/{id}/cancel`. The frontend never calls `/capture` and does not mark an order paid from a return URL alone.

Source integration and mocked browser tests do not establish that PostgreSQL, AI, or PayPal Sandbox are configured in a deployed environment. The API contract and feature matrix under `docs/` are historical snapshots; consult the current backend routers and schemas.

## Requirements

- Node.js 24.x, as declared in `package.json`.
- pnpm from the `packageManager` field and `pnpm-lock.yaml`; do not use npm or yarn.
- A JavaScript-enabled browser.
- A reachable FastAPI backend for REAL mode. DEMO does not need backend services.

## Install and run

From the repository root:

```bash
cd frontend
pnpm install --frozen-lockfile
cp .env.example .env
pnpm run dev
```

On Windows PowerShell, use `Copy-Item .env.example .env`.

Available scripts:

| Command | Purpose |
| --- | --- |
| `pnpm run dev` | Start the Vite development server. |
| `pnpm run test` | Run Vitest once. |
| `pnpm run lint` | Run ESLint. |
| `pnpm run build` | Create the production build in `dist/`. |
| `pnpm run preview` | Preview an existing build. |
| `pnpm run test:e2e` | Start Vite and run the Playwright critical-flow suite. |

## End-to-end tests

Playwright mocks `/api/**` at the HTTP layer, so it does not need PostgreSQL, AI, or PayPal credentials:

```bash
pnpm exec playwright install chromium   # first run only
pnpm run test:e2e
```

The suite covers a customer-token link that approves a quote and reconciles a mocked deposit, plus the workshop cookie-session gate and sign out. It is separate from Vitest.

## Modes and environment

| Variable | Required | Meaning |
| --- | --- | --- |
| `VITE_APP_MODE` | Set to `demo` for DEMO; use `real` for a connected deployment. | Selects the explicit application mode. A non-demo value does not configure an API by itself. |
| `VITE_API_BASE_URL` | Required for REAL. | Backend origin only, with no `/api` suffix or trailing slash. |

```dotenv
# Browser-only sample data
VITE_APP_MODE=demo
VITE_API_BASE_URL=

# Connected mode
VITE_APP_MODE=real
VITE_API_BASE_URL=https://your-backend-origin
```

All `VITE_*` values are compiled into public assets. Never place database, PayPal, AI, workshop-password, or customer-token secrets in them. Redeploy after changing a build-time variable.

### DEMO

With `VITE_APP_MODE=demo`, sample state persists under `localStorage` key `tallerclaro.demo.v1`. Payments and accounting output are illustrative. Receipt selection stores only the filename.

### REAL

With `VITE_APP_MODE=real` and `VITE_API_BASE_URL` set, the client calls the backend and propagates failures. If the URL is absent, the app enters UNCONFIGURED instead of exposing mock data.

Known limitations remain:

- Customer and payment recovery tokens live in `sessionStorage`; there is no email delivery flow.
- Receipt upload and expense reports have no backend implementation.
- PostgreSQL, AI, and PayPal Sandbox require separate live acceptance tests; mocked tests do not validate those providers.
- Accounting service failures are displayed as unavailable, never converted to financial zeroes.

## Project structure

```text
src/
  App.jsx                 Layout and hash routing
  components/             Shared UI, workshop auth, orders, customer, accounting
  pages/                  Workshop and customer screens
  hooks/                  Data, routing, session, speech, and assistant state
  services/
    apiClient.js          Demo/connected/unconfigured facade
    http.js               Fetch transport with cookies, CSRF, and ApiError
    adapters.js           API-to-UI normalization
    sessionStore.js       Customer token, CSRF, and payment recovery session state
    mockApi.js            Browser-only demo service
  styles/                 Global and application styles
e2e/
  critical-flows.spec.js  Playwright customer and workshop flows
docs/                     Historical contract, feature matrix, and PayPal URL notes
```

Keep demo operations isolated in `src/services/mockApi.js`; server-side pricing and payment verification remain authoritative.

## Routes

The app uses hash routing.

| Hash route | Screen |
| --- | --- |
| `#/dashboard` | Workshop dashboard. |
| `#/orders` | Workshop order list. |
| `#/quotes` | Workshop quote inbox. |
| `#/receipts` | Demo receipt-name view. |
| `#/accounting` | Workshop summary and assistant. |
| `#/order/{id}` | Workshop order detail. |
| `#/customer/new` | Customer project request. |
| `#/customer/quote` | Quote review, approval, and deposit checkout. |
| `#/customer/tracking` | Order tracking and balance checkout. |
| `#/customer/payment/return` | Payment reconciliation return. |
| `#/customer/payment/cancel` | Cancellation return and checkout resume. |

## Separate Vercel deployment

The frontend and FastAPI backend are separate Vercel projects. This directory is the frontend project root; `vercel.json` defines the frozen-lockfile install, Vite build, `dist` output, security headers, and immutable caching for hashed assets.

- Use Node 24.x and enable Corepack so Vercel honors `packageManager`.
- Set `VITE_APP_MODE=real` and `VITE_API_BASE_URL` to the production backend origin.
- Add the exact frontend origin to backend `TALLERCLARO_CORS_ORIGINS`.
- Point backend PayPal return/cancel URLs to the frontend HTTPS hash routes.
- Because the two projects use different sites, set `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none`; HTTPS is mandatory. If both later share one site, `lax` is preferred.
- Preview deployments have distinct origins. Use DEMO there unless those origins are deliberately added to CORS.

## Related documentation

- Root guide: `../README.md`
- Backend guide: `../Backend/BACKENDREADME.md`
- Database guide: `../database/README.md`
- PayPal return URL setup: `docs/PAYPAL_RETURN_URLS.md`
- Repository instructions: `../AGENTS.md`
