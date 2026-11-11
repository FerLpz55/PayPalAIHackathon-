# TallerClaro Backend

FastAPI backend for carpentry quotes, workshop orders, PayPal payments, and workshop financial summaries. It is a layered monolith. The code includes integration adapters, but the presence of an adapter does not prove that its provider or deployment is available.

## Status and verification boundary

Source includes domain rules, layered application use cases, direct PostgreSQL repositories, revocable workshop cookie sessions with CSRF, customer tokens, OpenAI-compatible AI services, Channel3 price search, and a server-side PayPal REST integration with idempotency, webhooks, and reconciliation.

Local verification on November 11, 2026 ran the fake-backed pytest suite: **481 passed**. This does not establish PostgreSQL persistence or external availability. PostgreSQL, AI, Channel3, PayPal Sandbox, and a deployed API were not contacted; actual SQL behavior, PayPal idempotency, and concurrent database captures remain unverified.

Important integration gaps:

- Backend startup requires a reachable PostgreSQL database and valid workshop bcrypt hash.
- Workshop authentication uses revocable `HttpOnly` cookies plus CSRF; Basic compatibility is disabled by default and the frontend does not send it.
- Customer links can be reissued by the workshop, but automatic email delivery is not included.
- PayPal webhooks, explicit sync/cancel, and background reconciliation exist; refunds, receipt upload, and an expense ledger are not implemented.
- Release mode rejects wildcard or insecure CORS origins.
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

The project supports Python 3.11 or newer. The local `.python-version` and the legacy Render definition select Python 3.11.10; Vercel selects a supported Python runtime from `pyproject.toml`. Dependency ranges live in `pyproject.toml`, and `requirements.txt` installs the project itself.

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

To create a bcrypt hash, use an approved local password-management process and place only the hash in TALLERCLARO_WORKSHOP_PASSWORD_HASH. The browser sends credentials only to the login endpoint and never stores the workshop password.

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

The legacy Render config declares `PYTHON_VERSION` and expects the host to supply `PORT`. Vercel imports `app/main.py` from the `Backend` project root. Do not expose AI, database, PayPal, or token secrets in `VITE_*` variables.

## Database setup

Supabase is used only as managed PostgreSQL. The app connects directly with psycopg using DATABASE_URL; it does not use Supabase Auth, PostgREST, Edge Functions, or Supabase SDKs.

For a new database, see ../database/README.md and apply database/schema.sql using the SQL Editor or psql. For an existing database, inspect the schema and apply only missing numbered migrations under an approved database change process. There is no migration runner. Startup does not automatically apply migrations.

The pool disables automatic prepared statements for Supavisor compatibility and the unit of work sets SERIALIZABLE isolation. A successful GET /api/health does not verify the database.

Current endpoints include:

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/health` | Comprobación de vida |
| POST | `/auth/login` | Iniciar sesión del taller (cookie + CSRF) |
| GET | `/auth/session` | Consultar la sesión vigente |
| POST | `/auth/logout` | Revocar la sesión y borrar cookies |
| GET | `/customer/context` | Cotización, pedido e intentos del cliente autenticado |
| POST | `/quotes` | Crear cliente y cotización draft |
| GET | `/quotes/{id}` | Consultar cotización |
| POST | `/quotes/{id}/generate` | Generar propuesta con IA |
| POST | `/quotes/{id}/approve` | Aprobar cotización y crear pedido |
| POST | `/quotes/{id}/reject` | Rechazar cotización |
| POST | `/quotes/{id}/customer-access` | Reemitir el enlace del cliente (solo taller) |
| GET | `/orders` | Listar pedidos del taller |
| GET | `/orders/{id}` | Consultar pedido con pagos y saldo |
| PATCH | `/orders/{id}` | Actualizar estado/fecha estimada |
| POST | `/orders/{id}/payments` | Crear intento de pago PayPal |
| POST | `/payments/{id}/capture` | Capturar pago en PayPal |
| POST | `/payments/{id}/sync` | Conciliar con PayPal: captura solo si está `APPROVED` |
| POST | `/payments/{id}/cancel` | Cancelar un intento pendiente sin liberar reservas inciertas |
| GET | `/payments/{id}` | Consultar intento de pago |
| POST | `/payments/webhook/paypal` | Webhook de PayPal verificado por firma |
| GET | `/accounting/summary` | Resumen financiero del taller |
| POST | `/accounting/assistant` | Preguntar al asistente contable |

## API routes and access

All routes use the `/api` prefix.

- Sin autenticación: `GET /api/health`, `POST /api/quotes` (devuelve el token del cliente) y `POST /api/payments/webhook/paypal`, que se autentica con la firma de PayPal.
- Taller: `POST /api/auth/login`, `GET /api/auth/session` y `POST /api/auth/logout`, además de `GET /api/orders`, `PATCH/DELETE /api/orders/{id}`, `POST /api/quotes/{id}/customer-access`, `GET /api/accounting/summary` y `POST /api/accounting/assistant`.
- El login verifica las credenciales contra `TALLERCLARO_WORKSHOP_PASSWORD_HASH` y emite una sesión opaca de 256 bits. Solo se guarda su SHA-256 en `tallerclaro.sesion_taller`; caduca a los 30 minutos de inactividad o 8 horas absolutas, es revocable y rota en cada login. Cambiar el hash bcrypt invalida las sesiones (huella de credenciales).
- Cookies: `__Host-tallerclaro_session` (`HttpOnly`, `Secure`, `SameSite` configurable con `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=lax|strict|none`, `Path=/`, sin `Domain`) y `__Host-tallerclaro_csrf` (legible por el JS del mismo origen). Usa `none` cuando el frontend (p. ej. Vercel) y la API estén en sitios distintos; exige HTTPS y CORS con credenciales. Las peticiones autenticadas por cookie que cambian estado exigen `X-CSRF-Token` igual al valor de la cookie CSRF y un `Origin` permitido.
- Basic está desactivado por defecto; solo se acepta con `TALLERCLARO_ENABLE_WORKSHOP_BASIC_AUTH=true` como compatibilidad explícita.
- Cliente: crear, consultar, conciliar (`sync`) y cancelar pagos, y `GET /api/customer/context`, requieren `X-Customer-Token` o `Authorization: Bearer`. El frontend no usa `/capture`: reconcilia con `/sync`, que solo captura si PayPal reporta `APPROVED`. La reemisión de acceso solo la puede solicitar el taller autenticado, revoca los tokens anteriores de la cotización y registra el evento; nunca se recupera acceso usando solo el ID.
- Lectura, aprobación, rechazo y generación de cotizaciones, y detalle de pedido, aceptan token del cliente propietario o sesión del taller mediante `PrincipalDep`, con validación de pertenencia antes y después de la llamada de IA. Un token de cliente inválido nunca concede privilegios del taller.

### Límites de abuso

- Los contadores viven en `tallerclaro.limite_consumo` y se incrementan con `INSERT ... ON CONFLICT DO UPDATE` (atómico, sin `DELETE`). El rechazo responde `429 RATE_LIMITED` con `Retry-After`.
- Login: 5 fallos por usuario e IP cada 15 minutos; un login correcto reinicia el contador.
- Creación de cotizaciones: 5 por minuto por IP. Generación: 5 cada 10 minutos por cotización y 100 por hora por taller; si el límite no está disponible no se llama a la IA. Catálogo de precios: 20 por minuto por actor.
- Los cuerpos JSON se limitan a 64 KiB (`TALLERCLARO_MAX_REQUEST_BODY_BYTES`) antes de procesarlos y responden `413 PAYLOAD_TOO_LARGE`.
- `X-Forwarded-For` solo se usa con `TALLERCLARO_TRUST_PROXY_HEADERS=true`; por defecto se emplea la IP de la conexión.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | /api/health | Public | Application liveness; not DB readiness |
| GET | /api/quotes | Workshop session | Workshop inbox; optional `status` filter (repeatable or comma-separated), `limit`, `offset` |
| POST | /api/quotes | Public | Create customer and draft quote; returns customer_token |
| GET | /api/quotes/{id} | Customer token or workshop session | Read quote; optional q query triggers price lookup |
| POST | /api/quotes/{id}/generate | Customer token or workshop session | AI quote generation/refinement |
| POST | /api/quotes/{id}/approve | Customer token or workshop session | Approve quote and create one order |
| POST | /api/quotes/{id}/reject | Customer token or workshop session | Reject quote |
| GET | /api/orders | Workshop session | Paginated workshop order list |
| GET | /api/orders/{id} | Customer token or workshop session | Order details, payment summaries, paid and remaining amounts |
| PATCH | /api/orders/{id} | Workshop session | Update status and/or estimated delivery date |
| POST | /api/orders/{id}/payments | Customer token | Create a PayPal payment intent |
| GET | /api/payments/{id} | Customer token | Read payment attempt |
| POST | /api/payments/{id}/capture | Customer token | Capture and verify payment with PayPal |
| GET | /api/accounting/summary | Workshop session | Aggregated order/payment totals |
| POST | /api/accounting/assistant | Workshop session | Ask AI to explain aggregate totals |

La configuración se define en `bootstrap/settings.py` y la plantilla es `.env.example`.
Se usa el prefijo `TALLERCLARO_`, con `DATABASE_URL` como alias recomendado para PostgreSQL.
El hash del taller no tiene un valor predeterminado utilizable. Cambia también el
secreto de tokens de ejemplo y configura `TALLERCLARO_CORS_ORIGINS` para el frontend.
Si el frontend y la API están en sitios distintos, usa
`TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none` (HTTPS y CORS con credenciales);
en el mismo sitio, el valor por defecto `lax` es suficiente.

`TALLERCLARO_ENVIRONMENT` acepta `development`, `test` y `release`. En `release`
el arranque rechaza secretos de plantilla, CORS con comodines o sin HTTPS,
PayPal incompleto (incluido `TALLERCLARO_PAYPAL_WEBHOOK_ID`), Live sin
`TALLERCLARO_ALLOW_LIVE_PAYMENTS=true` y un rol de base de datos superusuario o
con `DELETE`.

Receipt, expense, and refund endpoints are not implemented.

## Integrations

### AI

Quote generation and the accounting assistant use HTTPX with an OpenAI-compatible Chat Completions API. The quote parser validates JSON and line items; the domain calculates totals. The accounting assistant sends aggregate facts, not customer names or email addresses, according to the implementation. The timeout is 60 seconds. No provider credential or live response was verified.

### Channel3

The price lookup service uses HTTPX against Channel3 search, with a v0 fallback when v1 returns 404. Its timeout is 10 seconds. It is disabled by default and returns no results when no key is configured. The web provider mentioned in comments has no registered implementation.

### PayPal

The backend performs OAuth client-credentials and PayPal Orders v2 REST calls. It creates CAPTURE orders, obtains approval links, captures orders, and queries an order after a non-successful capture response. A stable PayPal-Request-Id is derived from the PayPal order ID.

Define `TALLERCLARO_PAYPAL_RETURN_URL` y `TALLERCLARO_PAYPAL_CANCEL_URL` como
URL HTTPS del frontend, por ejemplo `https://example.org/#/customer/payment/return`
y `https://example.org/#/customer/payment/cancel`. Se validan al construir el
procesador; con PayPal habilitado, una URL ausente o inválida impide el arranque.
`TALLERCLARO_PAYPAL_BRAND_NAME` fija la marca mostrada en PayPal. El checkout se
configura con `user_action=PAY_NOW` y `shipping_preference=NO_SHIPPING`.

**Idempotencia de creación.** Antes de llamar a PayPal se guarda el intento
pendiente con `clave_idempotencia` y `huella_solicitud` (SHA-256 de pedido, tipo,
importe y moneda). La misma clave se envía como `PayPal-Request-Id`. Un POST
repetido con el mismo contenido devuelve el mismo intento y la misma orden; un
cambio de importe responde `409`. Pasada `PAYMENT_IDEMPOTENCY_WINDOW` (15 min),
el intento debe conciliarse o cancelarse. El índice único parcial
`(id_pedido, tipo) WHERE estado = 'pending'` impide duplicados en PostgreSQL.

**Captura y conciliación.** Antes de capturar se persiste
`pedido.captura_en_curso`. Otros pagos del pedido quedan bloqueados hasta
completar y guardar el intento reservado. El POST de captura lleva una clave
`PayPal-Request-Id` estable por orden PayPal. Tras una respuesta HTTP no exitosa
se consulta la orden y se valida una captura completada. `POST /sync` consulta el
estado real: no captura si la orden sigue `CREATED`; persiste la captura si ya
está `COMPLETED`; captura solo si está `APPROVED` y el intento local sigue
`pending`; cancela el intento si está `VOIDED`. Si un intento cancelado o fallido
aparece como `COMPLETED` en PayPal, `sync` acredita esa captura sin volver a
capturar. Un fallo de transporte mantiene la reserva porque el resultado es
incierto. `POST /cancel` es local, rechaza pagos completados y no libera una
reserva de captura en curso.

Un fallo de conexión, timeout o protocolo HTTP se normaliza a
`PAYMENT_PROVIDER_ERROR` (HTTP 502), sin exponer secretos ni excepciones HTTPX.
Los errores mantienen la reserva. La recuperación local se probó con dobles, y
la idempotencia del proveedor y la concurrencia real siguen pendientes de
validación en Sandbox/PostgreSQL.

**Webhook.** `POST /api/payments/webhook/paypal` recibe el evento sin token de
cliente y exige `TALLERCLARO_PAYPAL_WEBHOOK_ID`. El backend llama a
`/v1/notifications/verify-webhook-signature` de PayPal antes de tocar la base:
sin `verification_status=SUCCESS` responde `401` y no registra nada. Los eventos
se deduplican en `tallerclaro.evento_paypal` con `ON CONFLICT DO NOTHING`; una
reentrega procesada responde `200 {"status": "duplicate"}` y un fallo queda como
`failed` para que la siguiente entrega lo reintente. Solo los eventos
`CHECKOUT.ORDER.*` y `PAYMENT.CAPTURE.*` provocan conciliación; reembolsos y
disputas se registran como `ignored`. La conciliación vuelve a consultar a PayPal:
nunca se acredita un pago usando solo el cuerpo del webhook.

**Conciliación en segundo plano.** Con `TALLERCLARO_PAYPAL_MODE=sandbox|live` y
`TALLERCLARO_PAYMENT_RECONCILIATION_ENABLED=true`, el `lifespan` inicia un bucle
que consulta los intentos `pending` con orden de PayPal sin actividad durante
`TALLERCLARO_PAYMENT_RECONCILIATION_MIN_AGE_SECONDS` (por lotes de
`TALLERCLARO_PAYMENT_RECONCILIATION_BATCH_SIZE`, cada
`TALLERCLARO_PAYMENT_RECONCILIATION_INTERVAL_SECONDS`) y los reconcilia con la
misma lógica de `sync`. Cada pago usa su propia unidad de trabajo y un fallo no
detiene el lote ni libera una reserva incierta. La tarea se cancela al apagar la
aplicación.

**Estado financiero y bloqueo.** El pedido expone `financial_status` derivado de
los pagos completados: `unpaid`, `deposit_paid` o `paid`. No se puede cancelar
ni borrar un pedido con pagos completados o con una captura en curso; esos casos
requieren resolución manual (reembolso fuera de este release).

## Business rules and persistence

- Currency is USD; monetary values use Decimal and are rounded to two decimals.
- AI proposes line items; server validates and calculates the total.
- Quote approval creates at most one order (code `TC-<1000 + quote id>`) and a 50% deposit.
- A confirmed deposit moves a `pending` order to `in_progress`; a full payment on a `pending` order marks it `paid`.
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

The backend and frontend are separate Vercel projects. Use `Backend` as the backend project root; Vercel detects `app/main.py` and imports the existing `tallerclaro.main:app`. Configure every server-side secret only in the backend project.

Serverless instances are not reliable schedulers. Set `TALLERCLARO_PAYMENT_RECONCILIATION_ENABLED=false` on Vercel and rely on the verified PayPal webhook plus explicit customer `sync`; use an external scheduled worker if periodic stale-payment reconciliation is required. The public `/api/health` route is liveness only and does not certify PostgreSQL connectivity.

For cross-site frontend/backend projects, use explicit HTTPS CORS origins and `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none`. Configure PayPal return/cancel URLs with the frontend origin. The checked-in `render.yaml` remains available for the legacy Render deployment path.

For database setup and migrations, see `../database/README.md`. For the frontend project, see `../frontend/README.md`. No deployed database migration is run automatically.
