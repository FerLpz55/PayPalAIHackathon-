# TallerClaro

**AI quoting, PayPal payments and plain-language bookkeeping for small carpentry workshops.**

A customer describes a piece of furniture by text or voice; AI turns it into an itemized quote grounded in live material prices (Channel3); the workshop reviews it; the customer approves and pays a 50% deposit and later the balance with PayPal; and the workshop asks an AI bookkeeper how much money is still pending.

This repository contains a React frontend, a FastAPI backend, and PostgreSQL schema/migration files. Built for the PayPal AI Hackathon 2026.

## Live demo and judge access

| | |
|---|---|
| **App** | https://tallerclaro.vercel.app |
| **API health** | https://tallerclaro-backend.onrender.com/api/health |
| **Workshop login** | user `taller` / password `TallerClaro2026!` |
| **PayPal Sandbox buyer** | `sb-yfmgc53787589@personal.example.com` / `<y6)O4-4` |

The API runs on Render's free tier: the first request after a period of inactivity can take about 50 seconds while the server wakes up. All payments use **PayPal Sandbox**; no real money is moved.

**Suggested end-to-end test (about 5 minutes):**

1. **Customer** (normal window): open https://tallerclaro.vercel.app/#/customer/new, describe a piece (e.g. *"Two-door white melamine wardrobe, 1.20 m wide, 1.80 m tall, 0.55 m deep"*), enter a name and email, and submit. The page shows *Waiting for the workshop*. Keep this window open and do not reload it: the customer access token lives in this tab.
2. **Workshop** (private/incognito window): open https://tallerclaro.vercel.app/#/dashboard, press **Sign in** with the workshop login above, go to **Quotes**, and press **Generate with AI** on the new request.
3. **Customer:** press **Check for updates**, review the itemized quote, and press **Approve quote**.
4. Press **Start PayPal Checkout** once, then **1. Open PayPal Checkout**. Log in with the Sandbox buyer and pay. PayPal returns to a TallerClaro tab that says *Payment attempt unavailable*; this is expected because that new tab has no customer token. Close it.
5. Back in the original customer tab, press **2. Verify & Confirm Payment**. The backend captures and verifies the payment with PayPal, and the tracking page shows the order (e.g. `TC-1022`) **In production** with the deposit paid.
6. Optional: on the tracking page, pay the remaining balance the same way; the balance becomes $0.
7. **Workshop:** open **Orders** and **Accounting**, and ask the assistant *"How much money is still pending?"*.

## Project status

Verified in production on November 11, 2026 (Vercel frontend + Render API + Supabase PostgreSQL + AI provider + Channel3 + PayPal Sandbox):

- Customer request → AI quote generation by the workshop → customer approval → PayPal deposit (create, approve, server-side capture) → order automatically moves to *In production* → PayPal balance payment → balance $0.
- Workshop sign-in, request inbox, orders and accounting dashboard against the live API and database.
- AI bookkeeping assistant answering in plain language from aggregated, verified payment totals.
- Live material price references from Channel3 on the quote page.
- Automated checks: backend **327 tests** passed; frontend **39 Vitest tests**, ESLint and production build passed.

## Features in source

- Customer project request with text input, presets, validation, and optional browser speech-to-text.
- Draft quote creation; AI-assisted estimate generation and clarification in the backend.
- Quote review, approval/rejection, line items, assumptions, and a 50% deposit model.
- Workshop order listing, status updates, customer order tracking, and payment summaries.
- Server-side PayPal Orders v2 create/capture flow with validation of capture status, identifier, currency, and amount.
- Workshop financial summary based on persisted orders and completed payments; AI assistant that explains aggregated figures.
- Live Channel3 price search for material references.
- Browser-only demo data and simulated payment/accounting/receipt behavior.
- Vercel frontend configuration and Render backend configuration.

See *Integration status* and *Known limitations* below for what is verified in production.

## Intended user flow

1. A customer submits a project request. The backend creates a customer, a draft quote, and a signed customer token.
2. The request appears in the workshop inbox (`GET /api/quotes`). The workshop generates the proposal with AI; the backend validates the AI response and calculates the total.
3. The customer reviews, approves, or rejects the quote. Approval creates one order with a short code (`TC-<1000 + quote id>`) and a 50% deposit.
4. The customer starts PayPal checkout. The backend creates the PayPal order, and the frontend opens its approval URL.
5. The backend captures and verifies the payment. A PayPal return URL alone never marks an order as paid. A confirmed deposit moves the order to *In production*.
6. The customer pays the remaining balance the same way. The workshop updates delivery status; delivery is guarded by full verified payment.

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

**REAL mode notes:** workshop credentials are entered through the sign-in dialog and held in memory until logout, a 401, or page reload, and are sent only over HTTPS (except loopback development). Quote generation is a workshop action. Set explicit CORS origins as a JSON list, e.g. `TALLERCLARO_CORS_ORIGINS=["https://tallerclaro.vercel.app"]`.

## API overview

All routes use the /api prefix. Route source is in Backend/src/tallerclaro/presentation/http/routers.

| Method | Endpoint | Purpose and access |
|---|---|---|
| GET | /api/health | HTTP liveness; does not test PostgreSQL |
| GET | /api/quotes | Workshop inbox (filter `status=draft,needs_information,...`); workshop Basic Auth |
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

There is no receipt upload, expense, refund, webhook, or payment-cancellation endpoint yet.

## Integration status

| Integration | Implementation | Runtime verification (Nov 11, 2026) |
|---|---|---|
| Frontend ↔ FastAPI | Fetch client, adapters, workshop sign-in, customer token headers | Verified in production (Vercel ↔ Render) |
| PostgreSQL / Supabase | psycopg pool, SQL repositories, schema and migrations | Verified in production |
| AI quote generation | OpenAI-compatible Chat Completions adapter with structured output validation | Verified in production |
| Accounting assistant | OpenAI-compatible service over aggregated totals only | Verified in production |
| Channel3 | Live product/price search for material references | Verified in production |
| PayPal | Server-side OAuth, Orders v2 create, approve, capture and verification | Deposit and balance verified end to end in PayPal Sandbox |
| Vercel / Render | `frontend/vercel.json`, `render.yaml` | Deployed and serving |

PayPal capture checks server-returned order/capture identifiers, status, amount, and currency. Capture reservations and PayPal request IDs prevent double capture. No webhook or background reconciliation is implemented yet.

## Known limitations

- The customer access token lives in the browser tab's session storage; there is no email delivery or cross-device recovery yet. The PayPal return tab therefore cannot verify the payment by itself; the customer confirms it from the original tab.
- If the AI asks for more information, the workshop adds the details from its inbox and regenerates; the customer cannot yet answer clarification questions directly.
- Workshop credentials are held in page memory (HTTP Basic over HTTPS). A server-side HttpOnly session is the planned hardening.
- No PayPal webhooks, refunds, or payment-cancellation endpoint yet. Press the PayPal checkout button once per payment.
- Receipt upload and expense tracking are not implemented; the accounting view covers orders and verified payments, not expenses or profit.
- Render's free tier sleeps when idle; the first request can take about 50 seconds.

## Tests and verification

Frontend (scripts in frontend/package.json):

    cd frontend
    pnpm install
    pnpm run test
    pnpm run lint
    pnpm run build

Backend (pytest configuration in Backend/pyproject.toml):

    cd Backend
    uv run --extra dev pytest -q

Results on November 11, 2026: backend **327 passed**; frontend **39 passed**, ESLint clean, production build OK. Backend unit/API tests use fakes; the live integrations were verified manually end to end in production (see *Project status*). The SQL acceptance file is database/tests/schema_test.sql; run it only against an isolated test database.

## Deployment

- Frontend: see frontend/README.md and frontend/vercel.json. Vercel root directory is frontend; the checked-in config uses frozen pnpm install, Vite build, dist output, and security headers.
- Backend: see Backend/BACKENDREADME.md and render.yaml. Render root directory is Backend; health path is /api/health. Configure all required secrets in the deployment environment.
- Database provisioning and migration steps: see database/README.md.

## Documentation

- [Frontend guide](frontend/README.md)
- [Backend guide](Backend/BACKENDREADME.md)
- [Database guide](database/README.md)
- [MVP integration plan](docs/informes/PLAN_MAESTRO_INTEGRACION_MVP.md)
- [Frontend/backend matrix](docs/informes/MATRIZ_FUNCIONAL_FRONTEND_BACKEND.md)
- [Issue acceptance matrix](docs/informes/MATRIZ_ISSUES_Y_CRITERIOS_ACEPTACION.md)
- [E2E verification report](docs/informes/INFORME_PRUEBAS_E2E.md)
- [Full MVP flow tracking issue #19](https://github.com/FerLpz55/PayPalAIHackathon-/issues/19)
- [OWASP review tracking issue #23](https://github.com/FerLpz55/PayPalAIHackathon-/issues/23)
- [Repository instructions](AGENTS.md)
- [Historical frontend API notes](frontend/docs/API_CONTRACT.md) - not the current API contract
- [Historical demo/real feature snapshot](frontend/docs/DEMO_VS_REAL_FUNCTIONALITY.md) - verify against source before relying on it
