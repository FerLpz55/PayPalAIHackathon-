# TallerClaro Backend

FastAPI backend for carpentry quotes, workshop orders, PayPal payments, and workshop financial summaries. It is a layered monolith. The code includes integration adapters, but the presence of an adapter does not prove that its provider or deployment is available.

## Status and verification boundary

Source includes domain rules, use cases, PostgreSQL repositories, workshop authentication, customer tokens, OpenAI-compatible AI services, Channel3 price search, and a server-side PayPal REST integration.

Local verification on November 9, 2026 ran the fake-backed pytest suite: **314 passed**. This does not establish PostgreSQL persistence or external availability. PostgreSQL, AI, Channel3, PayPal Sandbox, and a deployed API were not contacted; actual SQL behavior, PayPal idempotency, and concurrent database captures remain unverified.

Important integration gaps:

- Backend startup requires a reachable PostgreSQL database and valid workshop bcrypt hash.
- Workshop authentication uses HTTP Basic. The frontend now has a sign-in flow that keeps credentials in page memory and validates them through the existing read-only orders endpoint. It was checked only against a local HTTP stub, not FastAPI; quote generation remains workshop-protected when initiated from the customer flow.
- Customer tokens are returned from quote creation, but no email delivery or cross-device recovery path is included.
- No webhook, refund, payment-cancel endpoint, background reconciliation, receipt upload, or expense ledger was found. Workshop PATCH can set order status; a manually assigned paid status must not be treated as proof of a PayPal capture.
- The CORS setting defaults to wildcard in source; set explicit frontend origins for deployments.
- The current API health route is liveness only; it does not check PostgreSQL.

## Architecture

    src/tallerclaro/
      main.py                         FastAPI composition and lifespan
      bootstrap/settings.py           Environment-backed settings
      domain/                         Entities, values, money and status rules
      application/                    DTOs, interfaces, errors and use cases
        use_cases/                    Quotes, orders, payments, accounting, authorization
      infrastructure/
        db/                            psycopg pool, repositories, unit of work
        ai/                            Quote AI, accounting assistant, Channel3 lookup
        payment/                       PayPal processor, HTTP transport and response parsers
        security/                      Workshop bcrypt and customer token services
      presentation/http/
        routers/                       API route handlers
        schemas/                       Pydantic wire contracts
        dependencies.py                Authentication and dependency wiring
        exception_handlers.py          Domain/validation error mapping
        mappers.py                     Domain-to-response mapping
      tests/                           pytest suites and in-memory fakes

The domain owns money calculations, eligibility, and order state transitions. Application use cases coordinate repositories and provider interfaces. Routers handle HTTP/authentication and delegate to use cases. Infrastructure implements SQL and external HTTP calls. There is no ORM.

AI and PayPal calls are designed to happen outside SQL transactions. Payment capture uses a reservation, provider request ID, strict response parsing, and persisted verification before a payment counts as complete.

## Requirements

- Python 3.11 or newer.
- uv for local environment setup.
- PostgreSQL 15 or newer as documented by the database guide; Supabase is the managed option.
- A valid workshop bcrypt password hash.
- A database schema compatible with the checked-in repositories.
- Optional provider credentials for AI, Channel3 price search, and PayPal.

The Render service configuration selects Python 3.11.10. The local .python-version file also specifies 3.11.10. The project dependency ranges are in pyproject.toml; requirements.txt contains an editable project install.

## Install and start locally

From the repository root:

    cd Backend
    uv venv .venv

Activate the virtual environment:

    # macOS/Linux
    source .venv/bin/activate

    # Windows PowerShell
    .venv\Scripts\Activate.ps1

Install runtime and development dependencies:

    uv pip install -e '.[dev]'

Prepare Backend/.env from Backend/.env.example and configure a real PostgreSQL connection plus a valid bcrypt workshop password hash. In PowerShell, from Backend, start with Copy-Item .env.example .env. Do not commit .env or real credentials. The backend loads .env from the working directory. Generate the bcrypt hash locally with an approved password-management process; only the hash belongs in TALLERCLARO_WORKSHOP_PASSWORD_HASH. Start the API from Backend:

    fastapi dev src/tallerclaro/main.py

The API is served locally on 127.0.0.1:8000 by FastAPI CLI. Interactive API documentation is available at /docs. The backend fails startup when the workshop password hash is missing/invalid or the initial PostgreSQL connection fails.

To create a bcrypt hash, use an approved local password-management process and place only the hash in TALLERCLARO_WORKSHOP_PASSWORD_HASH. Frontend Basic credentials are entered by a workshop user and held only in browser memory; they are not a backend default or a substitute for a properly configured hash.

## Configuration

The settings are defined in src/tallerclaro/bootstrap/settings.py; the template is .env.example. Process environment variables take precedence over .env values. DATABASE_URL and TALLERCLARO_DATABASE_URL are accepted aliases; DATABASE_URL takes precedence if both are set in one source.

| Variable | Requiredness | Purpose |
|---|---|---|
| DATABASE_URL or TALLERCLARO_DATABASE_URL | Required for deployed DB use | PostgreSQL DSN; recommended Supabase Session Pooler with SSL. |
| TALLERCLARO_DATABASE_HOST | Required only if no DSN is set | PostgreSQL host; default localhost. |
| TALLERCLARO_DATABASE_PORT | Optional with local DB settings | PostgreSQL port; default 5432. |
| TALLERCLARO_DATABASE_NAME | Optional with local DB settings | Database name; default tallerclaro. |
| TALLERCLARO_DATABASE_USER | Optional with local DB settings | Database role; template uses tallerclaro_app. |
| TALLERCLARO_DATABASE_PASSWORD | Required for password-authenticated local DB settings | Database password. |
| TALLERCLARO_DATABASE_SSL_MODE | Optional | PostgreSQL SSL mode; template default is prefer. |
| TALLERCLARO_DATABASE_POOL_MIN_SIZE / TALLERCLARO_DATABASE_POOL_MAX_SIZE | Optional | Pool sizing; template defaults are 2 and 10. |
| TALLERCLARO_APP_NAME | Optional | FastAPI title. |
| TALLERCLARO_WORKSHOP_USERNAME | Optional | Workshop username; template default is taller. |
| TALLERCLARO_WORKSHOP_CARPENTER_ID | Optional | Carpenter scope; source default is 1. |
| TALLERCLARO_WORKSHOP_PASSWORD_HASH | Required at startup | Valid bcrypt hash. No usable default is provided. |
| TALLERCLARO_CUSTOMER_TOKEN_SECRET | Required for secure deployment | Strong secret for customer token hashing. Source/template placeholder must be replaced. |
| TALLERCLARO_CUSTOMER_TOKEN_TTL_HOURS | Optional | Token TTL in hours; default 72. |
| TALLERCLARO_CORS_ORIGINS | Required for secured cross-origin deployment | Comma-separated origins or JSON array. Set explicit frontend origins; source default is wildcard. |
| TALLERCLARO_AI_PROVIDER | Optional; default none | Supported values: none, openai, openrouter. |
| TALLERCLARO_AI_API_KEY | Required when AI is enabled | Provider API key. |
| TALLERCLARO_AI_MODEL | Optional | Model name; source fallback is gpt-4o-mini. |
| TALLERCLARO_AI_BASE_URL | Optional | OpenAI-compatible API base. Source default is OpenAI API base. |
| TALLERCLARO_PRICE_LOOKUP_PROVIDER | Optional; default none | Implemented factories: none and channel3. The web value in comments is not implemented. |
| TALLERCLARO_PRICE_LOOKUP_API_KEY | Required for Channel3 | Channel3 server-side key. |
| TALLERCLARO_PRICE_LOOKUP_BASE_URL | Optional | Channel3 API base; source has a provider default. |
| TALLERCLARO_PAYPAL_MODE | Optional; default none | Supported values: none, sandbox, live. |
| TALLERCLARO_PAYPAL_CLIENT_ID / TALLERCLARO_PAYPAL_CLIENT_SECRET | Required when PayPal is enabled | PayPal REST OAuth credentials; server-side only. |
| TALLERCLARO_PAYPAL_BASE_URL | Optional | Override inferred base URL. |
| TALLERCLARO_PAYPAL_RETURN_URL / TALLERCLARO_PAYPAL_CANCEL_URL | Required when PayPal is enabled | HTTPS frontend return/cancel routes. |

The Render config also declares PYTHON_VERSION and the host supplies PORT. Do not expose AI, database, PayPal, or token secrets in VITE_* variables.

## Database setup

Supabase is used only as managed PostgreSQL. The app connects directly with psycopg using DATABASE_URL; it does not use Supabase Auth, PostgREST, Edge Functions, or Supabase SDKs.

For a new database, see ../database/README.md and apply database/schema.sql using the SQL Editor or psql. For an existing database, inspect the schema and apply only missing numbered migrations under an approved database change process. There is no migration runner. Startup does not automatically apply migrations.

The pool disables automatic prepared statements for Supavisor compatibility and the unit of work sets SERIALIZABLE isolation. A successful GET /api/health does not verify the database.

## API routes and access

All routes use the /api prefix.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | /api/health | Public | Application liveness; not DB readiness |
| POST | /api/quotes | Public | Create customer and draft quote; returns customer_token |
| GET | /api/quotes/{id} | Customer token or workshop Basic | Read quote; optional q query triggers price lookup |
| POST | /api/quotes/{id}/generate | Workshop Basic | AI quote generation/refinement |
| POST | /api/quotes/{id}/approve | Customer token or workshop Basic | Approve quote and create one order |
| POST | /api/quotes/{id}/reject | Customer token or workshop Basic | Reject quote |
| GET | /api/orders | Workshop Basic | Paginated workshop order list |
| GET | /api/orders/{id} | Customer token or workshop Basic | Order details, payment summaries, paid and remaining amounts |
| PATCH | /api/orders/{id} | Workshop Basic | Update status and/or estimated delivery date |
| POST | /api/orders/{id}/payments | Customer token | Create a PayPal payment intent |
| GET | /api/payments/{id} | Customer token | Read payment attempt |
| POST | /api/payments/{id}/capture | Customer token | Capture and verify payment with PayPal |
| GET | /api/accounting/summary | Workshop Basic | Aggregated order/payment totals |
| POST | /api/accounting/assistant | Workshop Basic | Ask AI to explain aggregate totals |

Workshop authentication is HTTP Basic verified against TALLERCLARO_WORKSHOP_PASSWORD_HASH. Customer access uses X-Customer-Token or Authorization: Bearer. Quote and order access is checked against the principal in application use cases. Payment use cases receive the authorized quote scope from the token and validate its relationship to the payment/order.

No quote-list endpoint, receipt endpoint, expense endpoint, refund endpoint, PayPal webhook endpoint, or payment-cancellation endpoint is present in the current routers.

## Integrations

### AI

Quote generation and the accounting assistant use HTTPX with an OpenAI-compatible Chat Completions API. The quote parser validates JSON and line items; the domain calculates totals. The accounting assistant sends aggregate facts, not customer names or email addresses, according to the implementation. The timeout is 60 seconds. No provider credential or live response was verified.

### Channel3

The price lookup service uses HTTPX against Channel3 search, with a v0 fallback when v1 returns 404. Its timeout is 10 seconds. It is disabled by default and returns no results when no key is configured. The web provider mentioned in comments has no registered implementation.

### PayPal

The backend performs OAuth client-credentials and PayPal Orders v2 REST calls. It creates CAPTURE orders, obtains approval links, captures orders, and queries an order after a non-successful capture response. A stable PayPal-Request-Id is derived from the PayPal order ID.

The parser/use case validate completed status, order and capture IDs, currency, and exact expected amount before persisting a completed payment. A database capture reservation is implemented in source. Live Sandbox behavior, provider idempotency, and concurrent database captures remain unverified. There are no webhooks, refunds, backend cancellation route, background reconciliation, or manual resolution tool.

## Business rules and persistence

- Currency is USD; monetary values use Decimal and are rounded to two decimals.
- AI proposes line items; server validates and calculates the total.
- Quote approval creates at most one order and a 50% deposit.
- A payment counts only after backend verification with PayPal.
- Delivery requires fully verified payment.
- Customer token values are stored hashed in PostgreSQL; the plaintext token is returned by quote creation.
- No receipt/expense records, AI conversation history, or payment reconciliation history are implemented.

## Testing

Install the dev extra as above, activate the virtual environment, and from Backend run:

    python -m pytest

The configured pytest testpaths are tests. Suites cover domain, application, API behavior, and architecture/infrastructure contracts using fakes. They do not require live PostgreSQL, AI, or PayPal; passing tests cannot certify those external integrations.

The database acceptance script is database/tests/schema_test.sql. Run it only against a disposable test database because it executes SQL, even though its transaction rolls back. Do not run it against a deployed database without explicit approval.

No live-provider integration test or deployment smoke command is defined here. Validate database connectivity, AI, Channel3, and PayPal Sandbox separately in an approved staging environment. This README does not claim any tests were run.

## Deployment

render.yaml sets Backend as the service root, installs requirements.txt, starts Uvicorn on the platform PORT, and uses /api/health as the health-check path. Configure required variables in the Render environment. Do not assume health-check success means PostgreSQL is available.

For database setup/migrations, see ../database/README.md. For frontend environment and Vercel setup, see ../frontend/README.md. For project overview, see ../README.md.
