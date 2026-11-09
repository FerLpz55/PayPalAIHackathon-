# TallerClaro

TallerClaro is a PayPal AI Hackathon project for carpentry workshops. It is designed to collect customer project requests, prepare and review estimates, track workshop orders, and accept customer payments through PayPal. It also includes an illustrative accounting view and an AI assistant for workshop totals.

This repository contains a React frontend, a FastAPI backend, and PostgreSQL schema/migration files. Source code for an integration does not prove that a deployed service is configured or operational. Status below reflects the local frontend verification and fake-backed backend suite run on November 9, 2026; live service availability remains unverified.

## Project status

- The frontend has an explicit browser-only DEMO mode and a REAL mode that calls the configured API.
- The backend has source implementations for quote, order, payment, accounting, AI, price lookup, and PostgreSQL operations.
- PostgreSQL, an AI provider, Channel3, PayPal Sandbox, and a deployed API have not been verified as live services.
- The frontend now offers workshop Basic sign-in held in memory for the current page session. A local HTTP stub verified positive/negative login, logout, 401 expiry, and fail-closed behavior; FastAPI authentication and deployment TLS/CORS remain unverified.
- Quote creation and generation error states are explicit in the frontend. Generation remains workshop-protected and requires an authorized workshop session; no real AI proposal or full customer journey was verified.
- The frontend has no server-backed receipt upload or expense ledger. Demo receipt selection stores only a filename.
- No PayPal webhooks, refunds, backend cancellation route, or background payment reconciliation were found.
- Local verification: backend fake-backed suite 314 passed; frontend ESLint and production build passed. Vitest could not run because it is absent from local node_modules. No deployed-service request was made.

## Features in source

- Customer project request with text input, presets, validation, and optional browser speech-to-text.
- Draft quote creation; AI-assisted estimate generation and clarification in the backend.
- Quote review, approval/rejection, line items, assumptions, and a 50% deposit model.
- Workshop order listing, status updates, customer order tracking, and payment summaries.
- Server-side PayPal Orders v2 create/capture flow with validation of capture status, identifier, currency, and amount.
- Workshop financial summary based on persisted orders and completed payments; AI assistant that explains aggregated figures.
- Optional Channel3 price search implementation.
- Browser-only demo data and simulated payment/accounting/receipt behavior.
- Vercel frontend configuration and Render backend configuration.

These features are not all verified at runtime. See the integration and limitation sections below.

## Intended user flow

1. A customer submits a project request. The backend creates a customer, a draft quote, and a customer token.
2. The workshop generates a proposal. The backend validates the AI response and calculates the total.
3. The customer reviews, approves, or rejects the quote. Approval creates one order with a 50% deposit.
4. The customer starts PayPal checkout. The backend creates the PayPal order, and the frontend uses its approval URL.
5. The backend captures and verifies the payment. A PayPal return URL alone does not mark an order as paid.
6. The workshop updates production status. Delivery is guarded by full verified payment in the backend.

**Current flow gaps:** quote generation is protected by workshop Basic and requires an authorized workshop session; client clarification still lacks an appropriate customer-authenticated contract. Customer tokens remain in browser session storage and no email delivery or cross-device recovery flow was found. A complete customer journey must not be presented as verified.

## Architecture

| Layer | Implementation |
|---|---|
| Frontend | React 19, Vite, hash routes, reusable components, hooks, explicit demo/connected/unconfigured API modes |
| API | FastAPI routers and Pydantic request/response schemas under /api |
| Application/domain | Use cases, interfaces, entities, USD monetary rules using Decimal, status and payment eligibility |
| Infrastructure | psycopg repositories/unit of work, HTTPX AI and Channel3 clients, HTTPX PayPal REST transport/parsers, bcrypt workshop authentication, customer token service |
| Database | PostgreSQL in the dedicated tallerclaro schema; Supabase is used only as a managed PostgreSQL host |
| Deployment | Static frontend on Vercel; Python API service on Render |

The backend is a layered monolith, not a collection of microservices. There is no ORM. External provider calls are designed to happen outside SQL transactions.

### Technologies and declared versions

- Node.js 24.x and pnpm 12.14.0 are declared by frontend/package.json.
- React and React DOM are declared as ^19.3.1; Vite is ^8.3.5; Vitest is ^5.1.0.
- Backend declares Python >=3.11; Render configuration selects Python 3.11.10.
- Backend dependencies are specified in Backend/pyproject.toml: FastAPI, Pydantic Settings, Uvicorn, psycopg/pool, HTTPX, email-validator, and bcrypt. Development extras include pytest and pytest-asyncio.
- The PayPal, AI, and Channel3 integrations use HTTPX; no PayPal, OpenAI, or Supabase SDK is declared.

## Repository layout

    Backend/       FastAPI application, settings, integrations, and pytest suites
    database/      PostgreSQL schema, migrations, demo seed, and SQL acceptance script
    frontend/      React application, Vite config, frontend tests, and Vercel config
    AGENTS.md      Repository instructions and architecture constraints
    render.yaml    Render backend service definition
    README.md      Project entry point

## Requirements

- Node.js 24.x and pnpm 12.14.0 for the frontend.
- Python 3.11 or newer and uv for backend setup.
- PostgreSQL 15 or newer (Supabase is the documented managed option).
- psql or the Supabase SQL Editor for schema/migration administration.
- A reachable PostgreSQL database and a valid workshop bcrypt password hash to start the backend.
- Optional credentials for an AI provider, Channel3, and PayPal Sandbox, depending on the feature being exercised.

## Installation and local setup

### Frontend

From the repository root:

    cd frontend
    pnpm install --frozen-lockfile

The lockfile is committed. Use pnpm; the frontend README and package configuration do not specify npm or Yarn.

### Backend

From the repository root:

    cd Backend
    uv venv .venv

Activate the virtual environment, then install the project and development tools:

    # macOS/Linux
    source .venv/bin/activate
    uv pip install -e '.[dev]'

    # Windows PowerShell
    .venv\Scripts\Activate.ps1
    uv pip install -e '.[dev]'

Backend startup requires a database connection and a valid workshop bcrypt hash. The environment template contains placeholders only.

### PostgreSQL schema

For a new, isolated database, configure DATABASE_URL for the backend and apply the schema from the repository root:

    psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql

Optionally load the demo seed into a disposable database:

    psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/seeds/demo.sql

For an existing database, inspect its schema and apply only the required numbered migrations with the database owner's approval. There is no migration runner or migration-history table. Do not run schema, seed, migration, or SQL-test commands against a deployed database without an explicit operational plan and backup. See database/README.md.

## Configuration

Configuration templates:

- Frontend: frontend/.env.example
- Backend: Backend/.env.example
- Render: render.yaml
- Vercel: frontend/vercel.json

Copy/edit environment templates locally as needed; do not commit real credentials. Frontend VITE_* variables are compiled into public assets and must never contain secrets.

### Frontend variables

| Variable | Required | Meaning |
|---|---|---|
| VITE_APP_MODE | Required to explicitly select DEMO; optional for REAL if an API URL is set | Set to demo for browser-only samples, or real for a configured backend. |
| VITE_API_BASE_URL | Required for REAL mode | Backend origin only, without /api suffix or trailing slash. |

### Backend variables

| Variable | Requirement | Purpose |
|---|---|---|
| DATABASE_URL or TALLERCLARO_DATABASE_URL | Required for a real database connection; DATABASE_URL takes precedence when both are set in the same source | PostgreSQL connection string. |
| TALLERCLARO_DATABASE_HOST, PORT, NAME, USER, PASSWORD, SSL_MODE | Alternative when no database URL is set | Individual PostgreSQL connection settings. Defaults in the template are local placeholders, not production credentials. |
| TALLERCLARO_DATABASE_POOL_MIN_SIZE, TALLERCLARO_DATABASE_POOL_MAX_SIZE | Optional | Connection pool sizing. |
| TALLERCLARO_APP_NAME | Optional | FastAPI application title. |
| TALLERCLARO_WORKSHOP_USERNAME | Optional override; default username exists | Workshop Basic Auth username. |
| TALLERCLARO_WORKSHOP_CARPENTER_ID | Optional; defaults to 1 | Carpenter/workshop scope for workshop auth. |
| TALLERCLARO_WORKSHOP_PASSWORD_HASH | Required at startup | Valid bcrypt hash. There is no usable default password. |
| TALLERCLARO_CUSTOMER_TOKEN_SECRET | Required for secure deployment; code has an unsafe placeholder default | Secret used to hash customer link tokens. Replace the placeholder with a strong secret. |
| TALLERCLARO_CUSTOMER_TOKEN_TTL_HOURS | Optional; default 72 | Customer token lifetime. |
| TALLERCLARO_CORS_ORIGINS | Required for a secured cross-origin deployment | Comma-separated list or JSON array of allowed frontend origins. The code default is wildcard; set explicit origins in deployed environments. |
| TALLERCLARO_AI_PROVIDER | Optional; default none | none, openai, or openrouter. |
| TALLERCLARO_AI_API_KEY | Required when AI provider is enabled | Server-side provider API key. |
| TALLERCLARO_AI_MODEL | Optional | Model name; source fallback is gpt-4o-mini. |
| TALLERCLARO_AI_BASE_URL | Optional | OpenAI-compatible API base URL. |
| TALLERCLARO_PRICE_LOOKUP_PROVIDER | Optional; default none | Implemented factories are none and channel3. The web option in comments is not implemented. |
| TALLERCLARO_PRICE_LOOKUP_API_KEY | Required for Channel3 lookup | Server-side Channel3 key. |
| TALLERCLARO_PRICE_LOOKUP_BASE_URL | Optional | Channel3 API base URL. |
| TALLERCLARO_PAYPAL_MODE | Optional; default none | none, sandbox, or live. Use sandbox for integration verification. |
| TALLERCLARO_PAYPAL_CLIENT_ID and TALLERCLARO_PAYPAL_CLIENT_SECRET | Required when PayPal is enabled | PayPal REST OAuth credentials; server-side only. |
| TALLERCLARO_PAYPAL_BASE_URL | Optional | Overrides the base URL inferred from mode. |
| TALLERCLARO_PAYPAL_RETURN_URL and TALLERCLARO_PAYPAL_CANCEL_URL | Required when PayPal is enabled | HTTPS frontend routes for return and cancellation. |

Render supplies PORT and the checked-in Render configuration selects PYTHON_VERSION 3.11.10. Vercel reads VITE_* values at build time; redeploy after changing them.

## Run the application

### Browser-only DEMO

The frontend DEMO does not require the backend, database, AI, or PayPal:

    cd frontend
    # Set VITE_APP_MODE=demo in frontend/.env
    pnpm run dev

DEMO writes sample changes to localStorage. Payment actions are simulated and do not create PayPal payments. Receipt selection stores a filename only. Do not use demo figures as customer or accounting records.

### REAL mode

REAL mode requires a deployed or local API, PostgreSQL, a valid workshop hash, and a frontend API origin. Configure the backend environment and database before starting the API:

    cd Backend
    fastapi dev src/tallerclaro/main.py

Then configure frontend/.env with VITE_APP_MODE=real and VITE_API_BASE_URL set to the backend origin, and run:

    cd frontend
    pnpm run dev

The backend startup connects to PostgreSQL and rejects an invalid or missing workshop password hash. AI and PayPal default to none; their endpoints remain unavailable until configured. Configure an explicit CORS allowlist for the frontend origin.

**REAL mode limitations:** workshop Basic credentials are entered through the frontend sign-in dialog and held in memory until logout, a 401, or page reload. The client sends them only over HTTPS except for loopback development. This is a transitional browser authentication design, not an HttpOnly session. Quote generation remains workshop-protected. Use HTTPS, explicit CORS origins, and an authorized staging account before integration verification.

## API overview

All routes use the /api prefix. Route source is in Backend/src/tallerclaro/presentation/http/routers.

| Method | Endpoint | Purpose and access |
|---|---|---|
| GET | /api/health | HTTP liveness; does not test PostgreSQL |
| POST | /api/quotes | Create customer and draft quote; returns a customer token |
| GET | /api/quotes/{id} | Read quote; customer token or workshop Basic Auth |
| POST | /api/quotes/{id}/generate | Generate/refine quote; workshop Basic Auth |
| POST | /api/quotes/{id}/approve | Approve and create order; customer/workshop principal |
| POST | /api/quotes/{id}/reject | Reject quote; customer/workshop principal |
| GET | /api/orders | Paginated workshop order list; workshop Basic Auth |
| GET | /api/orders/{id} | Order details, payments, balance; customer/workshop principal |
| PATCH | /api/orders/{id} | Update status/delivery date; workshop Basic Auth |
| POST | /api/orders/{id}/payments | Create PayPal payment intent; customer token |
| GET | /api/payments/{id} | Read payment attempt; customer token |
| POST | /api/payments/{id}/capture | Capture/verify payment; customer token |
| GET | /api/accounting/summary | Aggregated order/payment totals; workshop Basic Auth |
| POST | /api/accounting/assistant | AI explanation of aggregate totals; workshop Basic Auth |

There is no receipt upload, expense, refund, webhook, quote-list, or payment-cancellation endpoint in the current route source.

## Integration status

| Integration | Implemented in source | Runtime verification |
|---|---|---|
| Frontend to FastAPI | Fetch client, mode guards, adapters, request headers; selected flows exercised against loopback HTTP stubs | No compatibility run against FastAPI or a deployed API |
| PostgreSQL/Supabase | psycopg pool, SQL repositories, schema and migrations | Not verified against a live database |
| AI quote generation | HTTPX OpenAI-compatible Chat Completions adapter | Provider defaults to none; real API not verified |
| Accounting assistant | HTTPX OpenAI-compatible service | Provider defaults to none; real API not verified |
| Channel3 | HTTPX price-search implementation | Provider defaults to none; no live lookup verified |
| PayPal | Server-side OAuth and Orders v2 create/capture parsing | Sandbox round trip not verified |
| Vercel/Render | Deployment configuration is checked in | Deployments not verified |

PayPal capture checks server-returned order/capture identifiers, status, amount, and currency. Capture reservations and request IDs exist in source, but provider idempotency and concurrent database capture behavior remain unverified. No webhook or background reconciliation was found.

## Known limitations

- Workshop Basic Auth is currently held in page memory; it has not been verified against a real API and remains readable by JavaScript on the page. A server-side session/BFF remains a production hardening option.
- Customer quote creation stores the returned customer token in sessionStorage. No email delivery or cross-device token recovery flow was found.
- Customer quote generation/refinement calls a workshop-only route. Failed generation is shown as an incomplete draft with an explicit error/retry path; customer clarification still lacks a customer-authorized backend contract.
- Quotes screen is not backed by a quote-list API; quote lookup by ID now hydrates the requested quote, but workshop lookup still needs a valid Basic session.
- Workshop order detail now fetches by ID and renders payment records from the response; it was exercised against a local stub, not FastAPI/PostgreSQL. Workshop PATCH can set order status manually; a paid status is not proof of PayPal capture.
- Order list requests subsequent pages and displays the range/total; pagination was exercised against a local stub, not FastAPI/PostgreSQL.
- Payment recovery depends on browser session storage. There is no endpoint to list or reconcile a customer's pending attempts by order, no webhook, no refund endpoint, and no backend payment-cancellation endpoint.
- Receipt upload and expense persistence are not implemented. Demo stores filenames and illustrative amounts only.
- Dashboard/accounting show request errors and unavailable values instead of substituting zero when the API fails. The backend summary covers orders and completed payments, not expenses or profit.
- Customer tokens are returned by quote creation but the repository has no email delivery path. The token service checks the used flag; source does not consume it on verification.
- The CORS code default is wildcard; deployments must set an explicit allowlist.
- frontend/docs/API_CONTRACT.md and frontend/docs/DEMO_VS_REAL_FUNCTIONALITY.md are historical snapshots and contain superseded claims. Use current routers/schemas and README status instead.

## Tests and verification

The frontend scripts, defined in frontend/package.json:

    cd frontend
    pnpm run test
    pnpm run lint
    pnpm run build
    pnpm run preview

The backend pytest configuration is in Backend/pyproject.toml. After installing the development extra and activating the virtual environment:

    cd Backend
    python -m pytest

Backend tests use fakes and do not establish live PostgreSQL, AI, or PayPal behavior. The SQL acceptance file is database/tests/schema_test.sql; run it only against an isolated test database because it executes SQL, even though the script rolls back its transaction.

No browser E2E script or CI workflow is defined. On November 9, 2026, the fake-backed backend suite passed **314 tests** using a workspace-local pytest temp directory; frontend ESLint and Vite build passed when invoked directly from installed binaries. Vitest did not run because its binary is absent, and `pnpm run` could not acquire the global store lock in the restricted environment. These checks do not verify staging API/DB, AI, Channel3, PayPal Sandbox, or persistence. Reproducible outcomes are recorded in INFORME_PRUEBAS_E2E.md.

## Deployment

- Frontend: see frontend/README.md and frontend/vercel.json. Vercel root directory is frontend; the checked-in config uses frozen pnpm install, Vite build, dist output, and security headers.
- Backend: see Backend/BACKENDREADME.md and render.yaml. Render root directory is Backend; health path is /api/health. Configure all required secrets in the deployment environment.
- Database provisioning and migration steps: see database/README.md.

## Documentation

- [Frontend guide](frontend/README.md)
- [Backend guide](Backend/BACKENDREADME.md)
- [Database guide](database/README.md)
- [MVP integration plan](PLAN_MAESTRO_INTEGRACION_MVP.md)
- [Frontend/backend matrix](MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md)
- [Issue acceptance matrix](MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md)
- [E2E verification report](INFORME_PRUEBAS_E2E.md)
- [Infrastructure blockers](PENDIENTES_INFRAESTRUCTURA_Y_CREDENCIALES.md)
- [Repository instructions](AGENTS.md)
- [Historical frontend API notes](frontend/docs/API_CONTRACT.md) - not the current API contract
- [Historical demo/real feature snapshot](frontend/docs/DEMO_VS_REAL_FUNCTIONALITY.md) - verify against source before relying on it
