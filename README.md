# TallerClaro

TallerClaro is a PayPal AI Hackathon project for carpentry quotes, customer payment journeys, and workshop order tracking. The repository is a monorepo with a React 19 + Vite frontend, a FastAPI layered monolith, and a PostgreSQL database designed for Supabase.

## Current project status

- **Frontend (`frontend/`)**: Workshop and customer screens with an explicit split between local **DEMO** mode (`mockApi` + `localStorage`) and **REAL** mode (`fetch` to the FastAPI backend). Includes a Vitest suite, ESLint, a production build, an interactive AI bookkeeping assistant (`AccountingAssistant`), and a Vercel configuration.
- **Backend (`Backend/`)**: Domain entities and monetary rules (`Decimal`, USD, 50 % deposit, status transitions), use cases (including AI bookkeeping assistant for workshop totals), PostgreSQL repositories, OpenAI-compatible AI quote generation and accounting assistant, PayPal Sandbox processing, workshop Basic Auth, and customer link tokens. Application abstractions live in `application/interfaces.py`; implementations live in `infrastructure/ai/` (`service.py` and `accounting_service.py`), `infrastructure/payment/` (processor facade plus separate HTTP transport and response parsing), `infrastructure/security/`, and `infrastructure/db/`. Monetary rules and payment eligibility live in the domain; capture reservations use a dedicated protocol exposed by the unit of work.
- **Database (`database/`)**: PostgreSQL schema in the dedicated `tallerclaro` schema, numbered migrations, and a self-contained, idempotent demo seed.
- **Pending live verification**: Supabase `DATABASE_URL`, real AI credentials, and a complete PayPal Sandbox round trip. Unit and API tests use in-memory fakes; passing them does not prove that external services are configured or reachable.
- **Current payment limits**: Capture reservations and retry recovery are implemented in source. Concurrent captures against PostgreSQL, provider idempotency, and operational recovery remain unverified; there is no background reconciliation or manual resolution tool.

## Architecture

```text
React 19 + Vite (frontend/)
        │  fetch /api  (REAL mode) or localStorage mock (DEMO mode)
        ▼
FastAPI layered monolith (Backend/src/tallerclaro/)
  presentation/http  →  application/use_cases  →  domain
                              │
                    application/interfaces.py
                              ▲
  infrastructure/db/repositories.py
  infrastructure/ai/service.py
  infrastructure/ai/accounting_service.py
  infrastructure/payment/paypal_processor.py
  infrastructure/payment/paypal_transport.py
  infrastructure/payment/paypal_parsing.py
  infrastructure/security/token_service.py
  infrastructure/security/workshop_auth.py
        │                    │                     │
        ▼                    ▼                     ▼
  PostgreSQL             AI provider          PayPal Sandbox
  (Supabase, schema      (OpenAI-compatible)  (server-side only)
   tallerclaro)
```

- `domain/`: entities and business rules; no FastAPI, Pydantic, ORM, or SDK dependencies.
- `application/`: use cases and `Protocol` interfaces.
- `infrastructure/`: PostgreSQL repositories, AI service, PayPal processor, and token service implementing the application interfaces.
- `presentation/http/`: routers, Pydantic schemas, authentication, and exception handlers.
- `bootstrap/` and `main.py`: settings, composition, and lifespan.

### Architectural invariants

- One unit of work per request; no mutable unit-of-work instance is shared between requests.
- No external network calls inside SQL transactions. AI and PayPal calls follow validate → call provider → reopen unit of work and revalidate → persist.
- Payment capture is strict: the backend verifies PayPal order/capture identifiers, `COMPLETED` status, USD currency, and the exact expected amount before crediting a payment.
- PostgreSQL and fake repositories must expose the same domain fields and behavior.
- Monetary calculations live in `domain/`, not in routers or frontend code.

## Business flow

1. The customer describes a project (text or voice input) and requests a quote. The backend creates the customer and a draft quote, returning a customer link token.
2. The workshop generates the proposal with AI. The response includes line items, assumptions, and possible missing information. The server validates and calculates the payable total.
3. The customer reviews the quote and approves or rejects it. Approval creates at most one order with a 50 % deposit.
4. For payments, the frontend asks the backend to create a PayPal order, redirects to the returned approval URL after validating it, and returns through a hash route. The backend captures and verifies the payment; a PayPal return URL alone never marks an order as paid.
5. The workshop updates production statuses. Delivery requires a verified full payment.

## Frontend

### Run locally

```bash
cd frontend
pnpm install
pnpm run dev
```

Use **pnpm only** (never `npm` or `yarn`). Node.js is pinned by `engines.node` (`24.x`) and pnpm by `packageManager` (`pnpm@12.14.0`) plus the committed `pnpm-lock.yaml`.

Copy `.env.example` to `.env` and choose a mode:

```dotenv
# DEMO: browser-only sample data under the localStorage key tallerclaro.demo.v1
VITE_APP_MODE=demo

# REAL: backend origin only (no /api suffix, no trailing slash)
VITE_APP_MODE=real
VITE_API_BASE_URL=https://api.example.com
```

The mode is decided in `frontend/src/services/apiClient.js` through `frontend/src/services/http.js`:

- `VITE_APP_MODE=demo` uses `mockApi` and `localStorage`; no PayPal charge is made.
- Otherwise, a non-empty `VITE_API_BASE_URL` enables real `fetch` calls to `/api`.
- If neither is configured, the app shows an "application mode is not configured" screen and never displays sample data.
- Requests never silently fall back to demo data. Some quote operations catch errors: initial generation failure leaves the draft available, and clarification can return the generation response if its refresh fails.

REAL integration still has an authorization gap: `http.js` sends stored workshop
credentials or falls back to `taller:demo-password`. The backend now requires a
configured bcrypt hash and supplies no default workshop password. The customer
request/clarification flow also invokes workshop-only generation; a customer
token alone cannot authorize that operation. These paths need integration work
before the complete customer journey can be presented as operational.

Never put AI, PayPal, database, or other secrets in `VITE_*` variables: they are embedded in the public bundle. Secrets belong only in `Backend/.env`.

### Routes

The app uses hash routes, so screens can be opened directly without a router dependency.

| Route | Screen |
| --- | --- |
| `#/dashboard` | Workshop summary and recent orders |
| `#/orders` | Searchable and filterable order list |
| `#/quotes` | Quote overview and estimates awaiting approval |
| `#/receipts` | Local receipt records and spending summary |
| `#/accounting` | Illustrative monthly income and expenses |
| `#/customer/new` | Customer project request and clarification flow |
| `#/customer/quote` | Quote breakdown, approval, and deposit checkout |
| `#/customer/tracking` | Order progress, payment summary, and balance checkout |
| `#/customer/payment/return` | PayPal return and backend capture verification |
| `#/customer/payment/cancel` | PayPal cancellation review and checkout resume |
| `#/order/TC-1048` | Workshop order details and status editor |

### Checks

```bash
cd frontend
pnpm run test
pnpm run lint
pnpm run build
pnpm run preview
```

`pnpm run test` runs the Vitest suites for URL safety, API adapters, session/payment recovery storage, and quote-title derivation. There is no browser-based end-to-end suite.

### Deploy on Vercel

The frontend is a static Vite build with hash routes, so no rewrite rules are needed. Import the repository into Vercel and set **Root Directory** to `frontend`. Install, build, output, security headers, and immutable asset caching come from `frontend/vercel.json`.

Environment variables are applied at build time; redeploy after changing them:

| Variable | Value | Required |
| --- | --- | --- |
| `ENABLE_EXPERIMENTAL_COREPACK` | `1` | Yes. Makes Vercel honor the exact pnpm version from `packageManager`. |
| `VITE_APP_MODE` | `demo` or `real` | Yes |
| `VITE_API_BASE_URL` | `https://<backend-origin>` (origin only) | Only in REAL mode |

For REAL mode, add the Vercel origin to `TALLERCLARO_CORS_ORIGINS` in the backend, and point PayPal return/cancel URLs to `https://<vercel-origin>/#/customer/payment/return` and `https://<vercel-origin>/#/customer/payment/cancel`. Preview deployments receive different `*.vercel.app` origins; use DEMO for Preview unless those origins are added to CORS.

## Backend

With Python 3.11+ (the repository `.venv` uses Python 3.14) and `uv`, from the repository root:

```bash
cd Backend
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env
fastapi dev src/tallerclaro/main.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

The API runs at `http://127.0.0.1:8000`; `/docs` exposes the generated OpenAPI UI.

### Configuration

All sensitive settings are read from environment variables. The templates are in `Backend/.env.example`:

- `DATABASE_URL` (recommended Supabase Session Pooler URL) or the individual `TALLERCLARO_DATABASE_*` fields.
- `TALLERCLARO_AI_PROVIDER`, `TALLERCLARO_AI_API_KEY`, `TALLERCLARO_AI_MODEL`.
- `TALLERCLARO_PAYPAL_MODE`, `TALLERCLARO_PAYPAL_CLIENT_ID`, `TALLERCLARO_PAYPAL_CLIENT_SECRET`.
- `TALLERCLARO_PAYPAL_RETURN_URL` and `TALLERCLARO_PAYPAL_CANCEL_URL` (HTTPS frontend routes when PayPal is enabled).
- `TALLERCLARO_WORKSHOP_USERNAME`, `TALLERCLARO_WORKSHOP_PASSWORD_HASH`.
- `TALLERCLARO_CUSTOMER_TOKEN_SECRET` and `TALLERCLARO_CUSTOMER_TOKEN_TTL_HOURS`.

AI and PayPal default to `none`; without credentials the services return `SERVICE_UNAVAILABLE`. A valid workshop bcrypt hash is required at startup; see the backend guide for generation. Startup fails if PostgreSQL cannot be reached. `GET /api/health` checks HTTP liveness only, not PostgreSQL connectivity.

### API (`/api`)

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Application liveness check |
| `POST` | `/api/quotes` | Create customer and draft quote (returns `customer_token`) |
| `GET` | `/api/quotes/{id}` | Retrieve quote details (workshop Basic Auth or `X-Customer-Token`) |
| `POST` | `/api/quotes/{id}/generate` | Generate AI quote breakdown or clarification questions (workshop) |
| `POST` | `/api/quotes/{id}/approve` | Approve quote and create order with a 50 % deposit |
| `POST` | `/api/quotes/{id}/reject` | Reject a pending quote |
| `GET` | `/api/orders` | List workshop orders with limit/offset pagination (workshop) |
| `GET` | `/api/orders/{id}` | Retrieve order details, payments, and remaining balance |
| `PATCH` | `/api/orders/{id}` | Update order status or estimated delivery date (workshop) |
| `POST` | `/api/orders/{id}/payments` | Create a PayPal Sandbox order for deposit or balance (`X-Customer-Token`) |
| `POST` | `/api/payments/{id}/capture` | Capture and verify a PayPal payment (`X-Customer-Token`) |
| `GET` | `/api/payments/{id}` | Retrieve payment attempt status (`X-Customer-Token`) |
| `GET` | `/api/accounting/summary` | Retrieve aggregated workshop financial totals (workshop) |
| `POST` | `/api/accounting/assistant` | Ask AI bookkeeping questions based on verified totals (workshop) |

### Authorization

- **Workshop**: HTTP Basic Auth via `require_workshop_credentials` for order listing/updates, quote generation, and accounting endpoints (`/api/accounting/*`).
- **Customer**: `X-Customer-Token` (or `Authorization: Bearer`) for payment creation, capture, and status lookup.
- Quote reads, approvals, rejections, and order detail accept a customer token or workshop Basic Auth depending on the route.

## Database

Supabase is used **only as a managed PostgreSQL server**. The backend connects directly with `psycopg` and `DATABASE_URL`; it does not use Supabase SDKs, Supabase Auth, PostgREST, or Edge Functions.

```text
database/
  schema.sql                    initial schema including migrations 001–003 for new databases
  migrations/                   numbered SQL changes
  seeds/demo.sql                self-contained, idempotent demo data
  tests/schema_test.sql         schema acceptance checks (rolled back)
```

Initialize a new Supabase project from the SQL Editor or `psql`:

```bash
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/seeds/demo.sql
```

The recommended connection is the Supabase **Session Pooler** on port `5432` with `sslmode=require` (IPv4-compatible). The `psycopg` pool disables automatic prepared statements and each unit of work opens a `SERIALIZABLE` transaction. Existing databases require migration 003 before deploying the capture reservation change.

The database lives in the `tallerclaro` schema, isolated from `public` and PostgREST. `schema.sql` revokes privileges from `PUBLIC`, `anon`, and `authenticated`. The optional `tallerclaro_app` role receives `SELECT/INSERT/UPDATE` and sequence usage but **no `DELETE`**.

Do not run migrations, seeds, or SQL tests that write data against a deployed database without explicit confirmation and a backup. Read-only checks are documented in [`database/README.md`](database/README.md).

## Tests

```bash
# Frontend
cd frontend
pnpm run test && pnpm run lint && pnpm run build

# Backend
cd ../Backend
.venv/bin/pytest
```

Backend tests use in-memory fakes and do not require PostgreSQL, AI, or PayPal. Frontend tests run in Node with Vitest. There is no CI workflow; verification is local.

On 2026-11-04, the backend suite `.venv/bin/pytest Backend` passed all 295 tests
with one `pytest-asyncio` deprecation warning under Python 3.14. Frontend checks
verified 21 Vitest tests, ESLint clean passing, and a successful Vite production build.
This does not verify deployed cloud services or concurrent SQL captures.

## Repository layout

```text
PayPalAIHackathon-/
├── Backend/          # FastAPI layered monolith, integrations, and pytest suite
├── database/         # PostgreSQL schema, migrations, demo seed, and SQL checks
├── frontend/         # React 19 + Vite app (pnpm, Vitest, Vercel config)
├── .gitignore
├── AGENTS.md         # Architecture rules and verified agent commands
├── LICENSE
└── README.md         # This guide
```

`AGENTS.md` contains the mandatory operating rules for agents (package managers, architecture invariants, Supabase constraints, and security). `Database` and backend details are expanded in [`database/README.md`](database/README.md) and [`Backend/BACKENDREADME.md`](Backend/BACKENDREADME.md); frontend details are in [`frontend/README.md`](frontend/README.md).

## Security notes

- Keep all credentials in `Backend/.env` or the deployment environment; never in `VITE_*` variables or committed files.
- The backend owns pricing, payment verification, authorization, and status transitions. The frontend never marks an order as paid on its own.
- PayPal approval URLs are validated against an HTTPS allowlist of PayPal hosts before redirecting.
- Vercel applies CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, and immutable caching for hashed assets.
- A successful build or test run does not establish that Supabase, the AI provider, or PayPal Sandbox are configured and operational.
