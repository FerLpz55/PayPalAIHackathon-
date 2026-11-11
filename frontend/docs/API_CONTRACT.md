# Frontend API Contract and Alignment Notes

**Evidence date:** 2026-11-02

> **Historical snapshot:** The inventory below describes the reviewed checkout,
> not the current API. As of 2026-11-09, workshop authentication uses revocable
> `HttpOnly` cookie sessions (`/api/auth/login|session|logout`) with CSRF and an
> allowed `Origin`; Basic is opt-in behind `TALLERCLARO_ENABLE_WORKSHOP_BASIC_AUTH`.
> Customer links are recovered with `X-Customer-Token` through
> `GET /api/customer/context` and reissued by the workshop via
> `POST /api/quotes/{id}/customer-access`. Payments reconcile with
> `POST /api/payments/{id}/sync` (capture only when PayPal reports `APPROVED`) and
> close with `POST /api/payments/{id}/cancel`; `/capture` is no longer used by the
> frontend. Orders expose `financial_status` (`unpaid|deposit_paid|paid`). Use
> [the backend guide](../../Backend/BACKENDREADME.md) and current routers/schemas
> as authority; use [the frontend guide](../README.md) for current integration
> notes. The older blocker statements below are historical.

**Repository evidence:** current checkout branch `feat/issue-22-demo-real-separation`, HEAD `1122c58`; backend route handlers, Pydantic schemas, dependencies, use cases, domain status constants, error handlers, app composition, configuration, and frontend call sites inspected.
**Scope:** Source-level contract inventory only. Route presence does not prove an endpoint is reachable, configured, deployed, or safe for production use. No backend code was changed.

## Contract status legend

- **Verified in source**: HTTP route, method, handler behavior, and schema fields were found in the checked-in backend code.
- **Proposed / unresolved**: documented or desired behavior not guaranteed by the handlers, schemas, and dependencies.
- **Runtime unverified**: not exercised against a running backend; database, AI, and PayPal configuration is not established by this document.

## Authentication and deployment boundary

These are source observations, not credentials or an approved browser-authentication design:

- `GET /api/health` and all quote routes currently declare no authentication dependency. Quote reads expose quote data by integer ID; backend owners must decide intended public/customer access before production use.
- Workshop order list/detail/update routes use HTTP Basic through `require_workshop_credentials`. The dependency reads the configured username but compares the password to the literal `demo-password`, not `workshop_password_hash`, and returns `CarpenterId(1)` after success. Do not embed Basic credentials in the frontend or rely on this placeholder as a production auth contract.
- Payment create/capture/read routes require the `X-Customer-Token` header. The dependency verifies the token and returns `(customer_id, quote_id)`, but payment handlers currently discard that identity. See the resource-scoping warning below.
- `CustomerTokenService.create()` exists in infrastructure but no HTTP issuance/delivery route or caller was found. `verify()` checks expiration and the stored `used` flag but does not mark a token used. The configured default TTL is 72 hours; one-time use, issuance, revocation, and browser delivery are not implemented as an API contract.
- PayPal OAuth credentials are used by the backend adapter; they are not frontend credentials and must never be sent by the browser.
- No CORS middleware/origin setup or frontend API-origin configuration was found in app composition. Cross-origin browser connectivity is unestablished.

The source uses the standard HTTP Basic header for workshop routes (`Authorization: Basic <base64(username:password)`) and the literal `X-Customer-Token: <customer link token>` header for payment routes. These header formats do not establish a safe way for a browser to obtain or store either credential.

Backend settings use the `TALLERCLARO_` prefix. AI defaults to provider `none`; PayPal defaults to mode `none`; database defaults are placeholders. These defaults and source configuration do not prove a usable environment. Do not place provider credentials in `VITE_*` variables.

## Issue #22 frontend integration status

The frontend has a partial REAL-mode integration for quote/order retrieval and PayPal checkout routes, while DEMO uses `frontend/src/services/mockApi.js` and local browser state. A source-verified route and successful frontend build do not establish that the backend is running or configured. Current UI feature classifications and file-level evidence are in [DEMO_VS_REAL_FUNCTIONALITY.md](./DEMO_VS_REAL_FUNCTIONALITY.md); PayPal return configuration blockers are in [PAYPAL_RETURN_URLS.md](./PAYPAL_RETURN_URLS.md).

| Backend source group | Route handlers present in checked-in source | Frontend connection | Runtime status |
|---|---|---|---|
| Health | `GET /api/health` | None | Not exercised from this frontend; response establishes liveness only. |
| Quotes | `POST/GET /api/quotes`; `POST /api/quotes/{quote_id}/generate`, `/approve`, `/reject` | REAL calls backend directly; DEMO uses local `mockApi`. | Not runtime-verified. AI and database configuration remain unverified. |
| Orders | `GET /api/orders`, `GET/PATCH /api/orders/{order_id}` | REAL calls these routes; DEMO uses local state. | Not runtime-verified. Superseded: the client now uses the workshop cookie session and sends no Basic credentials. |
| Payments | `POST /api/orders/{order_id}/payments`, `POST /api/payments/{payment_id}/capture`, `GET /api/payments/{payment_id}` | REAL uses backend create/status/capture and PayPal Sandbox approval redirect; DEMO simulation is local and labeled. | Not E2E-verified. PayPal return/cancel URLs remain hardcoded to `example.com`; browser storage loss cannot recover attempts. |

The detailed request/response, status, authentication, and error notes below remain source-level observations, not frontend guarantees. Issue #22 added no backend endpoint and proposed no backend contract change.

Base path is `/api`. Numeric path parameters are parsed as integers, while entity IDs are serialized as strings in JSON. Backend monetary values are serialized as JSON numbers in USD; domain money uses two-decimal Decimal rounding.

## Verified endpoint inventory

### Health

| Method and path | Request | Success response | Auth |
|---|---|---|---|
| `GET /api/health` | No body | `200`: `{"status":"ok"}`. Schema also permits `degraded`, but handler always returns `ok`. | None |

This is a liveness response. It does not verify database, AI, or PayPal availability. The application lifespan catches database connection exceptions and continues startup; the health handler then still returns `{"status":"ok"}`. Do not treat that response as dependency readiness.

### Quotes

Quote routes have no authentication dependency in the current handlers. This is confirmed source behavior, not a recommendation that they be public.

| Method and path | Request | Success response | Auth |
|---|---|---|---|
| `POST /api/quotes` | JSON: `{ "customer": { "name": string, "email": valid email, "phone": string \| null }, "carpenter_id": integer, "request": string }`. `phone` is optional/nullable. `customer`, `name`, `email`, `carpenter_id`, and `request` are required by the schema. | `201` Quote response: `id`, `customer_id`, `carpenter_id`, `request`, `description`, `items`, `currency`, `total`, `deposit_amount`, `balance_amount`, `status`, optional `assumptions`, `missing_info`, `created_at`, `updated_at`. New quote use case sets status `draft`, description/total null, and items empty. Handler serializes `missing_info` as null here. | None |
| `GET /api/quotes/{quote_id}` | Integer path ID; no body | `200` same Quote response structure. | None |
| `POST /api/quotes/{quote_id}/generate` | Integer path ID; no body is declared or read by handler. | `200`: `{ id, status, description, items, total, assumptions, missing_info }`. Current handler does not populate `assumptions`; schema default is null. If status is `needs_information`, handler sets `missing_info` to an empty array; otherwise null. | None |
| `POST /api/quotes/{quote_id}/approve` | Integer path ID; no body | `200` Order response: `id`, `quote_id`, `code`, `total`, `deposit_amount`, `balance_amount`, `currency`, `status`, `estimated_delivery_date`, `created_at`, `updated_at`. Approval use case creates at most one order per quote and returns existing order if the quote was already approved and order exists. | None |
| `POST /api/quotes/{quote_id}/reject` | Integer path ID; no body | `200` same Quote response shape. | None |

Quote line item response shape: `{ id: string, type: string, description: string, unit: string, quantity: number, unit_amount: number, amount: number }`. Domain constants define `material`, `labor`, `other`; the response schema itself types `type` as an unrestricted string.

Source-defined quote statuses: `draft`, `needs_information`, `pending_review`, `approved`, `rejected`. The AI adapter can receive `missing_info` and `assumptions`, but those values are not copied onto the Quote entity by the current use case, and the generate route currently returns an empty `missing_info` array for `needs_information`. Do not rely on actual reasons or assumptions being returned until corrected and tested.

### Orders

`GET /orders`, `GET /orders/{order_id}`, and `PATCH /orders/{order_id}` require workshop HTTP Basic credentials via `require_workshop_credentials`.

| Method and path | Request | Success response | Auth |
|---|---|---|---|
| `GET /api/orders?limit=20&offset=0` | Query: `limit` integer 1–100, default 20; `offset` integer >= 0, default 0. No body. | `200`: `{ orders: Order[], total: integer, limit: integer, offset: integer }`. | Workshop Basic |
| `GET /api/orders/{order_id}` | Integer path ID; no body | `200`: Order fields plus `payments: PaymentSummary[]`, `paid_amount: number`, `remaining_balance: number`. `PaymentSummary`: `id`, `type`, `amount`, `status`, `paypal_order_id`. | Workshop Basic |
| `PATCH /api/orders/{order_id}` | JSON fields are optional: `{ "status": string \| null, "estimated_delivery_date": "YYYY-MM-DD" \| null }`. No other fields in schema. | `200` Order response. | Workshop Basic |

Order response shape: `{ id, quote_id, code, total, deposit_amount, balance_amount, currency, status, estimated_delivery_date, created_at, updated_at }`. IDs are string-serialized. `estimated_delivery_date` is nullable date. Source-defined order statuses are `pending`, `paid`, `in_progress`, `delivered`.

Domain transition rules: `pending -> paid|in_progress`; `paid -> in_progress`; `in_progress -> delivered`; `delivered` has no outgoing transitions. Delivery is rejected unless completed payments total the order total. Updating to `delivered` also checks payment completion in the use case. The API schema does not enumerate allowed status strings, so invalid values are rejected by domain logic, not schema enum validation.

### Payments

Payment create, capture, and lookup require `X-Customer-Token`. No handler declares an `Authorization` bearer/PayPal token input; PayPal credentials are server-side configuration.

| Method and path | Request | Success response | Auth |
|---|---|---|---|
| `POST /api/orders/{order_id}/payments` | JSON: `{ "type": "deposit" \| "balance" }`; schema technically accepts any string, domain logic accepts only these values. | `200`: `{ payment_id, paypal_order_id, amount, currency, approval_url }`; `approval_url` may be null. | `X-Customer-Token` |
| `POST /api/payments/{payment_id}/capture` | Integer path ID; no body | `200`: `{ payment_id, status, paypal_order_id, paypal_capture_id, amount, currency, paid_at }`. Capture is done server-side through the payment processor. | `X-Customer-Token` |
| `GET /api/payments/{payment_id}` | Integer path ID; no body | `200`: `{ id, order_id, type, amount, currency, status, paypal_order_id, paypal_capture_id, created_at, paid_at }`. | `X-Customer-Token` |

Source-defined payment types: `deposit`, `balance`. Source-defined payment statuses: `pending`, `completed`, `failed`, `cancelled`. The current create/capture flow creates `pending` and on successful capture writes `completed`; error/cancellation status transitions are not exposed as frontend endpoints in the inspected router. A completed balance/payment total may update order status to `paid`.

**Capture response caveat:** on the first successful capture, both the checked-in PayPal adapter and the API test fake construct `CapturedPayment` with `payment_id=0`. `CapturePayment` returns that adapter result and the router serializes it, so the first capture response currently reports `"payment_id": "0"` rather than the persisted payment's ID. The already-completed retry branch instead returns the persisted ID. This inconsistency is source-verified and must be fixed or explicitly contracted before a frontend relies on the capture response identifier.

**Payment/order status caveat:** a partial deposit capture leaves an order in `pending`; only when completed payments reach the total does capture attempt to set the order to `paid`. The domain allows `pending -> paid`, but does not allow `in_progress -> paid`; the capture use case still attempts that transition if an in-progress order becomes fully paid, which can raise a conflict. The intended and corrected transition behavior needs backend confirmation. Failed/cancelled statuses exist in the domain, but the current routes do not persist those transitions; a failed provider call can leave the payment pending.

**Order PATCH payment caveat:** `PATCH /api/orders/{order_id}` accepts `status: "paid"` from `pending` under the domain transition table, without checking completed payment records. The full-payment check is applied when the target status is `delivered`. Therefore the current order `paid` status is not, by itself, proof of a PayPal-verified payment. This conflicts with the product rule that a success page must not mark an order paid. Backend enforcement and the authoritative meaning of `paid` must be agreed before the frontend relies on this status.

## Frontend data-integrity rules

- Treat quote/order totals, deposit/balance values, payment status, and order status returned by an agreed API as server-owned. The browser must not make a client-calculated amount authoritative for checkout.
- Keep payment status distinct from fulfillment status. A customer return/redirect from PayPal is not confirmation; capture and a verified server response/read are required before showing a real successful payment.
- Do not treat order status `paid` as verified payment until the PATCH bypass above is corrected or the backend provides an independently verified payment field/contract.
- Delivery must remain blocked until the backend confirms full completed payment. The use case currently checks this on `delivered`, but runtime and authorization behavior remain unverified.

**Important source-level limitation:** the token dependency verifies a token and returns `(customer_id, quote_id)`, but payment handlers discard this `token_data`; the use cases load the order/payment solely by supplied numeric ID. The checked-in handlers therefore do not demonstrate that the supplied token is scoped to the requested order/payment. Backend owners must resolve this authorization boundary before frontend use.

## Error behavior verified in source

| Case | Current response behavior |
|---|---|
| Domain `NOT_FOUND` | `404` JSON `{ "code": "NOT_FOUND", "message": string }` |
| Domain `CONFLICT` | `409` JSON `{ "code": "CONFLICT", "message": string }` |
| Domain `VALIDATION_ERROR` | `422` JSON `{ "code": "VALIDATION_ERROR", "message": string }` |
| Request schema validation | `422` JSON `{ "code": "VALIDATION_ERROR", "message": "Request validation failed", "field_errors": [{ "field": string, "message": string }] }` |
| Domain `UNAUTHORIZED` | `401` JSON `{ "code": "UNAUTHORIZED", "message": string }` |
| Missing/invalid workshop or customer credentials | FastAPI `401` response uses `{ "detail": string }`; missing workshop credentials also set `WWW-Authenticate: Basic`. This differs from the domain error envelope. |
| Other DomainError codes (including `SERVICE_UNAVAILABLE`, `AI_RESPONSE_INVALID`, and payment-provider codes) | The registered handler falls back to `400` and returns `{ "code": string, "message": string }`. The docs' claim of `503` for unavailable services is not implemented by this mapping. |
| Unhandled runtime/database/transport errors | No normalized response contract is established by the inspected exception handlers; framework defaults may apply. |

The current error contract is not uniform. Frontend should not encode undocumented `503` behavior as guaranteed until backend owners agree and implement it.

## Schema-shaped request and response examples

These examples show field names and types from the checked-in Pydantic schemas and handlers. Placeholder values are illustrative, not captured from a running service. They do not guarantee that a database/provider is configured or that a request will succeed.

### Create a quote

`POST /api/quotes` has no auth dependency in the current handler. `phone` may be omitted or set to null; the other fields shown are required.

```json
{
  "customer": {
    "name": "<customer name>",
    "email": "customer@example.invalid",
    "phone": null
  },
  "carpenter_id": 1,
  "request": "<customer carpentry request>"
}
```

The handler responds `201` with a Quote schema. A newly created quote is `draft`; description and total are null, and items are empty. IDs are serialized as strings:

```json
{
  "id": "<quote id>",
  "customer_id": "<customer id>",
  "carpenter_id": "<carpenter id>",
  "request": "<request>",
  "description": null,
  "items": [],
  "currency": "USD",
  "total": null,
  "deposit_amount": null,
  "balance_amount": null,
  "status": "draft",
  "assumptions": null,
  "missing_info": null,
  "created_at": "<ISO 8601 timestamp or null>",
  "updated_at": "<ISO 8601 timestamp or null>"
}
```

`POST /api/quotes/{quote_id}/generate` has no request body in its current handler. The response shape is `{ id, status, description, items, total, assumptions, missing_info }`. For `needs_information`, the handler currently returns `missing_info: []` rather than the AI adapter's reasons. It does not pass `assumptions`, so the schema default is null. For a successful `pending_review` result, each item has `id`, `type`, `description`, `unit`, `quantity`, `unit_amount`, and `amount`. Do not infer useful clarification content from the current response.

### List and update orders

`GET /api/orders?limit=20&offset=0` requires workshop Basic Auth and responds with `{ orders: Order[], total, limit, offset }`. Each Order has `id`, `quote_id`, `code`, `total`, `deposit_amount`, `balance_amount`, `currency`, `status`, `estimated_delivery_date`, `created_at`, and `updated_at`. The response omits customer name, email, and project description.

`PATCH /api/orders/{order_id}` requires workshop Basic Auth and a JSON body matching `UpdateOrderRequest`:

```json
{
  "status": "in_progress",
  "estimated_delivery_date": "2026-11-15"
}
```

Both fields are optional/nullable in the schema; an empty object is schema-valid, but the route still requires a JSON body. Status strings are not constrained by a Pydantic enum and are validated later by domain transitions. A delivery-date-only update does not change status.

### Create and capture a payment

`POST /api/orders/{order_id}/payments` requires `X-Customer-Token` and accepts:

```json
{ "type": "deposit" }
```

The request schema types `type` as a string; domain logic currently accepts `deposit` or `balance`. The handler returns `{ payment_id, paypal_order_id, amount, currency, approval_url }`, where `approval_url` is nullable. With the configured PayPal adapter, the backend creates a server-side PayPal `CAPTURE` order and looks for an `approve` link. The adapter's return and cancel URLs are hardcoded to `https://example.com/payment/return` and `https://example.com/payment/cancel`.

After browser approval, the API offers `POST /api/payments/{payment_id}/capture` (same customer-token dependency, no body) and `GET /api/payments/{payment_id}`. Capture returns `{ payment_id, status, paypal_order_id, paypal_capture_id, amount, currency, paid_at }`; see the capture response caveat above. The frontend return route checks backend identity and status before capture, then queries again before showing confirmation. The PayPal adapter checks provider status `COMPLETED` before reporting capture success. The return/cancel URLs still need backend configuration; see [PAYPAL_RETURN_URLS.md](./PAYPAL_RETURN_URLS.md).

The create-payment response shape is:

```json
{
  "payment_id": "<payment id>",
  "paypal_order_id": "<PayPal order id>",
  "amount": 5.0,
  "currency": "USD",
  "approval_url": "<approval URL or null>"
}
```

`GET /api/payments/{payment_id}` returns the stored Payment fields:

```json
{
  "id": "<payment id>",
  "order_id": "<order id>",
  "type": "deposit",
  "amount": 5.0,
  "currency": "USD",
  "status": "pending",
  "paypal_order_id": "<PayPal order id or null>",
  "paypal_capture_id": null,
  "created_at": "<ISO 8601 timestamp or null>",
  "paid_at": null
}
```

The first successful capture currently has the same field shape but may report `"payment_id": "0"` as noted above. The capture response schema requires non-null PayPal order/capture IDs and `paid_at`; source/runtime failure paths have not been tested end to end.

### Order response shapes

Quote approval returns an Order object directly (not an envelope):

```json
{
  "id": "<order id>",
  "quote_id": "<quote id>",
  "code": "TC-<generated code>",
  "total": 10.0,
  "deposit_amount": 5.0,
  "balance_amount": 5.0,
  "currency": "USD",
  "status": "pending",
  "estimated_delivery_date": null,
  "created_at": "<ISO 8601 timestamp or null>",
  "updated_at": "<ISO 8601 timestamp or null>"
}
```

The `GET /api/orders/{order_id}` detail response adds payments and calculated payment totals:

```json
{
  "id": "<order id>",
  "quote_id": "<quote id>",
  "code": "TC-<generated code>",
  "total": 10.0,
  "deposit_amount": 5.0,
  "balance_amount": 5.0,
  "currency": "USD",
  "status": "pending",
  "estimated_delivery_date": null,
  "created_at": "<ISO 8601 timestamp or null>",
  "updated_at": "<ISO 8601 timestamp or null>",
  "payments": [
    {
      "id": "<payment id>",
      "type": "deposit",
      "amount": 5.0,
      "status": "pending",
      "paypal_order_id": "<PayPal order id or null>"
    }
  ],
  "paid_amount": 0.0,
  "remaining_balance": 10.0
}
```

`GET /api/orders` wraps Order objects in the pagination envelope documented above. The list/detail response schemas do not include the customer or quote request content needed by several current frontend screens.

### Validation error example

The request-validation handler formats FastAPI schema errors as:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "field_errors": [
    {
      "field": "body.request",
      "message": "Field required"
    }
  ]
}
```

The field path/message values depend on the actual validation failure. Credential failures use FastAPI's `detail` shape instead, and unhandled errors do not have a normalized response contract.

## Comparison with current frontend

The frontend does not call HTTP endpoints. `frontend/src/services/mockApi.js` and `useDemoData.js` use seeded objects plus `localStorage` key `tallerclaro.demo.v1`; no `fetch`/Axios client exists. Related UI callers include `useQuoteRequest.js`, `QuoteReviewPage.jsx`, `OrderDetailPage.jsx`, `AccountingPage.jsx`, `ReceiptsPage.jsx`, and `OrderTrackingPage.jsx`.

| Frontend demo model/operation | Backend counterpart | Gap |
|---|---|---|
| `createQuote({ customer, email, description, project })` | `POST /quotes` expects customer object `{name,email,phone}`, `carpenter_id`, and `request`; it creates only a draft. `POST /quotes/{id}/generate` is separate. | Map form fields and determine carpenter ID; follow create then generate; UI needs draft/needs-information/pending-review states. No project/measurements fields in request contract. |
| Quote `id` like `TC-1050`; `project`, `customer`, `items[{label,amount,kind}]`, `total`, `deposit`, `balance` | Numeric backend IDs serialized as strings; `request`, `description`, `items[{description,unit,quantity,unit_amount,amount,type}]`, `total`, `deposit_amount`, `balance_amount`, `currency`. | Separate display code from ID; server contract has no `project`/measurement fields and requires field mapping. Keep totals server authoritative. |
| `approveQuote()` changes local quote and creates local order | `POST /quotes/{quote_id}/approve` returns Order. | No workshop/customer authorization on quote approval route; customer/workshop approval actor and UI permission are undefined. Response order ID differs conceptually from quote ID; client must retain both. No customer token is returned. |
| `simulatePayment('deposit'|'balance')` | Create payment intent, browser approval via returned `approval_url` (or agreed SDK), then `POST capture`; `GET payment` | Mock directly changes local paid/order status. Backend has no cancellation/return callback endpoint. PayPal adapter currently hardcodes `https://example.com/payment/return` and `/payment/cancel`; production frontend return URL cannot be configured through request. Runtime/provider not verified. |
| Local order list/detail/status update | `GET /orders`, `GET /orders/{id}`, `PATCH /orders/{id}` | Requires workshop Basic Auth; no safe client credential/session contract. Backend exposes numeric IDs/code and lacks customer/project display fields expected by UI. Status vocabulary differs (`quote_sent`, `ready_to_finish` are demo-only). |
| Local `paid`, `spent`, and receipt records | Order detail includes `paid_amount`, `remaining_balance`, payments. | Backend has no receipt list/upload/amount verification endpoints; no expenses/accounting aggregate endpoint. |
| `OrderTrackingPage` looks up local quote/order by quote ID | No customer-readable order or quote lookup endpoint with `X-Customer-Token` is exposed. | Tracking cannot safely be built against current routes; payment endpoints' token dependency alone does not provide order data. |
| User-input customer PII stored in local browser demo | `POST /quotes` sends customer name/email/phone and request | Data retention/privacy/error semantics and token delivery need team agreement before sending real customer data. |
| Capture response | `POST /payments/{id}/capture` serializes `CapturedPayment.payment_id` returned by the adapter. | Current first-capture adapters return `0` for that field; repeat capture after completion returns the persisted ID. Backend should align the response with the persisted payment ID before frontend integration. |
| Payment completion while an order is in progress | Capture attempts to mark an order `paid` when completed amounts reach the total; the domain transition table does not allow `in_progress -> paid`. | Confirm/fix the payment-versus-fulfillment transition and define the expected response when the balance is captured during production. |

## Missing or unverified contracts

### No matching route found in the checked-in route handlers

- Customer token creation, delivery, refresh, revocation, or a customer link exchange endpoint. `CustomerTokenService.create()` exists, but no route/use-case caller was found. Token service verifies expiration and a `used` flag; no route-side issuance or consumption workflow is present.
- Customer-authorized `GET /orders/{id}`, quote retrieval, or other tracking read endpoint. Existing order reads require workshop Basic Auth; payment GET returns payment only.
- Receipt upload/list/delete/review or receipt amount verification endpoints.
- Accounting/receipts aggregates or dashboard metric endpoint (can potentially be derived from orders/payments if frontend receives all required fields and pagination is handled).
- Payment cancellation/failure status update or provider-return reconciliation endpoint.
- A contract for frontend-configurable PayPal return/cancel URLs. Current adapter hardcodes placeholder example.com routes.
- Session/login/token exchange for workshop credentials; no session endpoint is present.

### Present in source, runtime or behavior unverified

- All route groups listed above: database connectivity/migrations and deployment reachability were not tested.
- The backend API tests use an in-memory unit of work and fake AI/payment adapters; the test fixture overrides workshop-credential and customer-token dependencies. Passing those tests does not verify configured credentials, token scoping, database persistence, CORS, or external provider behavior.
- AI generation: adapter defaults to unconfigured when provider is `none`; current error is `400 SERVICE_UNAVAILABLE`, not documented `503`.
- PayPal create/capture: adapter defaults to unconfigured when mode is `none`; configuration and successful sandbox round-trip are unverified.
- `GET /health` only confirms handler liveness; it does not establish dependencies are usable.
- CORS middleware/origin configuration was not found in app composition. Browser cross-origin access is therefore not established.
- Workshop Basic Auth checks configured username but compares password to the literal `demo-password` instead of using `workshop_password_hash`; the code comment says the hash behavior is a placeholder. Do not rely on this as a production authentication contract.
- AI adapter accepts `missing_info` and `assumptions`, but current use case/route do not preserve them into the response as expected.
- PayPal capture response parsing and failure mapping exist in source but have not been validated against live Sandbox behavior.

## Unresolved backend-team questions / blockers

1. Which deployed API base URL, environment, CORS origins, and API version should the frontend use? Is there a reproducible non-production environment with migrated database and configured dependencies?
2. Can the backend publish/lock OpenAPI and sample success/error responses matching the code? Are `404`, `409`, `422`, and service/provider failures stable, and will unavailable integrations return `503` instead of current `400`?
3. Who may create, generate, approve, and reject quotes? Should customer quote routes be public, authenticated, or customer-token scoped? What data may `GET /quotes/{id}` expose?
4. What is the intended `carpenter_id` source/configuration? Is it always `1` for this demo? Is `phone` nullable and can it be omitted? Are there validation length limits?
5. How will a customer token be issued and delivered? Is it one-time or reusable? What are expiry, revocation, and refresh rules? Current repo has no issuance route; `verify()` checks the stored `used` flag but does not consume/mark a token. “One-time” behavior is not implemented by the checked-in route flow.
6. Will token validation enforce that the order/payment being accessed belongs to token's customer/quote? Current payment handlers discard verified token identity; confirm and fix backend object-level authorization before integration.
7. What endpoint will allow a customer to retrieve quote/order/progress under their link token? Should it return customer-facing display data and verified payments? Current tracking UI has no matching read contract.
8. What are authoritative quote status and line-item semantics? Will generation return actual `missing_info` and `assumptions`? Should `POST /generate` accept follow-up information after `needs_information`? Current body is absent and current route returns an empty array for missing information.
9. Approval naming is inconsistent: quote domain statuses include `pending_review` and `approved`, while the frontend demo button represents customer approval and route creates an order. Which actor approves, and is this endpoint intended to be idempotent for frontend retries?
10. What should order status do after deposit capture? Current implementation leaves partial deposit orders in `pending`; transition to `in_progress` is a separate workshop PATCH. Confirm intended business transition and update UI mapping.
11. Will the API expose customer/project/request fields with orders, or should frontend fetch each quote? Current `OrderResponse` contains no customer name/email or project description; order detail doesn't embed quote.
12. How should workshop authentication work in a browser? Shared Basic credentials must not be embedded in the public bundle. Will the backend provide a safe session/BFF/auth mechanism, or is workshop API use intentionally restricted to a trusted demo client?
13. How will PayPal approval return/cancel URLs be configured per frontend deployment? Is browser redirect to returned `approval_url` the chosen flow, and what exact `payment_id`/order state must be re-fetched after return?
14. Are payment attempts idempotent? A completed deposit conflicts, but pending/failed/cancelled deposit attempts can create additional rows and balance attempts have no duplicate guard. What retry/cancel semantics should the frontend implement?
15. Are receipt upload and accounting included in this API delivery? If so, specify multipart limits, storage, malware/content validation, amount verification lifecycle, and read authorization. No routes currently cover them.
16. Confirm whether the frontend should use the current snake_case wire contract directly or a documented API version/adapter, and what date/time/currency formatting constraints apply.
17. Fix and document the first-capture response identifier: should `payment_id` be the persisted payment record ID on both first capture and idempotent repeat?
18. Confirm the order/payment transition when a balance is captured for an `in_progress` order. Current capture logic attempts a disallowed `in_progress -> paid` transition after total payment.
19. Should workshop `PATCH /orders/{id}` be allowed to set `paid` without matching completed payments? This is currently permitted from `pending` and weakens `paid` as an authoritative payment state.

## Safe frontend work before backend answers

- Keep the current demo path labeled as local/simulated; do not route live-looking actions to nonexistent or unconfigured APIs.
- #21 accessibility/responsive review and #22 demo-separation documentation have frontend changes in this checkout. Their completion does not establish backend connectivity or replace the recorded review limitations.
- Prepare a frontend field/status mapping document and page data requirements; do not freeze a production API client around unresolved auth, token, tracking, or error assumptions.
- Add UI design for loading, empty, validation, unauthorized, conflict, dependency-unavailable, and payment-cancelled states as presentation-only work, retaining explicit demo status; do not add mock endpoints or make these states claim backend support.
- Improve UI data handling/types and component boundaries for separating quote ID from order ID and separating payment status from fulfillment status, provided this does not imply network functionality.
- Contract/API client implementation, workshop dashboard integration, customer tracking integration, quote flow integration, and PayPal checkout must wait for the relevant backend answers and a reachable configured environment.

## Source references in this repository

- `Backend/src/tallerclaro/presentation/http/routers/{health,quotes,orders,payments}.py`
- `Backend/src/tallerclaro/presentation/http/schemas/{health,quotes,orders,payments,common}.py`
- `Backend/src/tallerclaro/presentation/http/dependencies.py`
- `Backend/src/tallerclaro/presentation/http/exception_handlers.py`
- `Backend/src/tallerclaro/domain/entities.py`
- `Backend/src/tallerclaro/application/use_cases/{quotes,orders,payments}.py`
- `Backend/src/tallerclaro/infrastructure/security/token_service.py`
- `Backend/src/tallerclaro/infrastructure/{ai/adapter.py,payment/paypal_adapter.py}`
- `frontend/src/services/mockApi.js`, `frontend/src/hooks/{useDemoData,useQuoteRequest}.js`, relevant frontend pages

No endpoint in this document is claimed operational without runtime verification.
