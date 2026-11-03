# Project: TallerClaro Security, AI, Persistence & Dual-Mode Frontend Integration

## Architecture
Simple layered monolith (presentation, application, domain, infrastructure, bootstrap):
- `domain/`: Pure entities and domain exceptions (`ForbiddenError`), without framework dependencies.
- `application/`: DTOs (`CreatedQuoteResult`, `OrderDetailResult`, `AccessPrincipal`), Ports (`CustomerTokenRepository`, `UnitOfWork`), and Use Cases (`quotes.py`, `orders.py`, `payments.py`) implementing resource-level authorization.
- `infrastructure/`: DB repositories (`PostgresQuoteRepository` without DELETE), AI adapter (`OpenAIAIService` with resilient error handling and strict item validation), Unit of Work (`CustomerTokenService`).
- `bootstrap/`: Application configuration (`Settings` with workshop credentials and CORS origins) and FastAPI initialization (`CORSMiddleware`).
- `presentation/`: FastAPI HTTP routers (`quotes.py`, `orders.py`, `payments.py`), typed dependencies (`Annotated`, `require_workshop_credentials`, `require_customer_token`, `require_quote_or_workshop_principal`), Pydantic v2 schemas (`extra="forbid"`, `str_strip_whitespace=True`), and exception handlers (semantical status codes, avoiding `StarletteDeprecationWarning`).
- `frontend/`: React + Vite SPA using `pnpm`. Dual-mode `apiClient.js` (Real FastAPI backend via `VITE_API_BASE_URL` vs local demo fallback via `mockApi.js`), session token storage (`tallerclaro.session.v1`), and UI adaptation for `needs_information`, `assumptions`, and `measurements`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | `ForbiddenError` Exception | Domain & Application exception with code `FORBIDDEN` mapped to HTTP 403 | M1 | R1 |
| 2 | `Quote` Entity Extensions | Add `assumptions: list[str]`, `missing_info: list[str]`, and `mark_needs_information(missing_info: list[str])` | M1 | R1 |
| 3 | Application DTOs | Add `CreatedQuoteResult`, `OrderDetailResult`, and `AccessPrincipal` in `dtos.py` | M1 | R1 |
| 4 | Token Repository Port & UoW | Define `CustomerTokenRepository` protocol, add `tokens` property to `UnitOfWork` | M1 | R1 |
| 5 | Quote Use Cases Authorization & Logic | `CreateQuote` normalizes customer data, generates customer token, returns `CreatedQuoteResult`. `GetQuote`, `ApproveQuote`, `RejectQuote` authorize principal. `GenerateQuoteProposal` supports `draft`, `needs_information`, `pending_review`, `additional_info`, and sets `assumptions`/`missing_info`. | M1 | R2 |
| 6 | Order Use Cases Authorization & Safety | `GetOrder` executes within `with self._uow:`, authorizes principal, loads payments/customer data, returns `OrderDetailResult`. `UpdateOrder` validates `carpenter_id`. | M1 | R2 |
| 7 | Payment Use Cases Authorization | `CreateOrderPayment`, `CapturePayment`, `GetPayment` receive `authorized_quote_id` and prevent IDOR against `order.quote_id`. | M1 | R2 |
| 8 | Test Fakes & In-Memory Unit Tests | Add `FakeCustomerTokenRepository` to `fakes.py`, update existing 24 tests to pass with new signatures. | M1 | R1, R2, AC |
| 9 | `PostgresQuoteRepository` No-DELETE Sync | Synchronize quote items via `UPDATE` for existing rows and `INSERT` for new rows; eliminate `DELETE FROM detalle_cotizacion`. | M2 | R3 |
| 10 | Infrastructure Token Service & UoW | Expose `CustomerTokenService` as `tokens` property on `PostgresUnitOfWork`. | M2 | R3 |
| 11 | Resilient & Validating AI Service | Enclose remote calls with token-masked `DomainError(code="SERVICE_UNAVAILABLE")`; strictly validate items (`material|labor|other`, positive qty, non-negative price, non-empty description) raising `DomainError(code="AI_RESPONSE_INVALID")`. | M2 | R3 |
| 12 | Bootstrap Settings & CORS | Add `workshop_password`, `workshop_carpenter_id`, `cors_origins` to `Settings`, configure `CORSMiddleware` in `main.py`. | M2 | R4 |
| 13 | Typed HTTP Dependencies | Implement `Annotated` dependencies: `require_workshop_credentials` (`secrets.compare_digest`), `require_customer_token` (`X-Customer-Token`), `require_quote_or_workshop_principal`. | M2 | R4 |
| 14 | Pydantic v2 Schemas & Customer Token | Add `extra="forbid"`, `str_strip_whitespace=True` to input schemas, add `customer_token` to `QuoteResponse`. | M2 | R4 |
| 15 | Semantical HTTP Exception Handlers | Map domain errors to 401, 403, 404, 409, 422 (`status.HTTP_422_UNPROCESSABLE_CONTENT`), 502, 503 without deprecation warnings. | M2 | R4 |
| 16 | Router Auth Protection & Delegation | Protect routes in `quotes.py`, `orders.py`, `payments.py` with dependencies and delegate to use cases. | M2 | R4 |
| 17 | API Integration Tests | Add `tests/api/test_auth.py` and `tests/api/test_quotes.py` verifying 401 unauthenticated, 403 IDOR prevention, and `needs_information` flow. | M2 | AC |
| 18 | Dual-Mode Frontend Client (`apiClient.js`) | Support Connected Mode (`VITE_API_BASE_URL`) and Local Demo Mode (`mockApi.js`), `sessionStorage` (`tallerclaro.session.v1`), and UI response adapters. | M3 | R5 |
| 19 | UI Hooks & Pages Integration | Update `useQuoteRequest.js`, `useDemoData.js`, `OrderDetailPage.jsx`, `OrderTrackingPage.jsx`, `AccountingPage.jsx`, `ReceiptsPage.jsx` to use `apiClient`. | M3 | R5 |
| 20 | `QuoteReviewPage` Clarification Flow | Render `missing_info`, input form for additional information, render `assumptions`, guard against missing `measurements`, approve quote via `apiClient`. | M3 | R5 |
| 21 | Frontend Build & Lint Verification | Ensure `cd frontend && pnpm run lint` and `cd frontend && pnpm run build` pass with zero errors. | M3 | R5, AC |
| 22 | Final Verification & E2E Validation | Run full Backend pytest suite (`cd Backend && .venv/bin/pytest -v`) and Frontend pnpm build/lint, verifying all ACs. | M4 | AC |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend Domain & Application | Features 1, 2, 3, 4, 5, 6, 7, 8 | none | DONE |
| M2 | Backend Infrastructure & Presentation | Features 9, 10, 11, 12, 13, 14, 15, 16, 17 | M1 | DONE |
| M3 | Frontend Dual Client & UI Integration | Features 18, 19, 20, 21 | M2 (interface contracts) | IN_PROGRESS |
| M4 | Final Verification & Acceptance | Feature 22 | M1, M2, M3 | PLANNED |

## Interface Contracts

### Domain & Application Contracts
- `ForbiddenError(DomainError)`: `code="FORBIDDEN"`, message explains forbidden access.
- `Quote`:
  - `assumptions: list[str] = field(default_factory=list)`
  - `missing_info: list[str] = field(default_factory=list)`
  - `mark_needs_information(self, missing_info: list[str]) -> None`: sets status to `needs_information`, updates `missing_info`.
- `dtos.py`:
  - `CreatedQuoteResult(quote: Quote, customer_token: str)`
  - `OrderDetailResult(order: Order, payments: list[Payment], customer_name: str | None, customer_email: str | None, project_request: str | None)`
  - `AccessPrincipal(kind: Literal["customer", "workshop"], customer_id: CustomerId | None = None, quote_id: QuoteId | None = None, carpenter_id: CarpenterId | None = None)`
- `ports.py`:
  - `CustomerTokenRepository`:
    - `create(self, customer_id: CustomerId, quote_id: QuoteId) -> str`
    - `verify(self, token: str) -> tuple[CustomerId, QuoteId] | None`
  - `UnitOfWork.tokens: CustomerTokenRepository`

### HTTP API Contracts
- `POST /api/quotes`: returns `QuoteResponse` with `customer_token: str` (also returns 201 Created).
- `GET /api/quotes/{quote_id}`: requires `require_quote_or_workshop_principal`. 401 if unauthenticated, 403 if principal is customer with non-matching `quote_id`.
- `POST /api/quotes/{quote_id}/proposal`: requires workshop principal. Accepts `additional_info: str | None`. Returns `QuoteResponse` (status `pending_review` or `needs_information`).
- `POST /api/quotes/{quote_id}/approve`: requires `require_quote_or_workshop_principal`. Returns `QuoteResponse`.
- `POST /api/quotes/{quote_id}/reject`: requires `require_quote_or_workshop_principal`. Returns `QuoteResponse`.
- `GET /api/orders/{order_id}`: requires `require_quote_or_workshop_principal`. Queries order, payments, and customer details within transaction, returns `OrderDetailResponse`.
- `PATCH /api/orders/{order_id}`: requires workshop principal (`carpenter_id`).
- `POST /api/orders/{order_id}/payments`: requires `require_customer_token`. Verifies token's `quote_id == order.quote_id` (403 otherwise).
- `POST /api/orders/{order_id}/payments/{payment_id}/capture`: requires `require_customer_token`. Verifies token's `quote_id == order.quote_id` (403 otherwise).

### Frontend Client Contracts (`apiClient.js`)
- `sessionStorage` key: `tallerclaro.session.v1`. Stores `{ customerToken, activeQuoteId, customerName, customerEmail, workshopCredentials }`.
- `apiClient.createQuote(data)`: returns adapted quote with `id`, `items`, `deposit`, `balance`, `missing_info`, `assumptions`.
- `apiClient.getQuote(id)`: returns adapted quote.
- `apiClient.submitMissingInfo(quoteId, additionalInfo)`: calls `POST /api/quotes/{quoteId}/proposal` with `additional_info`.
- `apiClient.approveQuote(quoteId)`: calls `POST /api/quotes/{quoteId}/approve`.
- `apiClient.getOrder(orderId)`: returns adapted order with payments and customer details.
- `apiClient.updateOrderStatus(orderId, status)`: calls `PATCH /api/orders/{orderId}`.

## Code Layout
- Backend Domain: `Backend/src/tallerclaro/domain/`
- Backend Application: `Backend/src/tallerclaro/application/`
- Backend Infrastructure: `Backend/src/tallerclaro/infrastructure/`
- Backend Bootstrap: `Backend/src/tallerclaro/bootstrap/`
- Backend Presentation: `Backend/src/tallerclaro/presentation/`
- Backend Tests: `Backend/tests/`
- Frontend: `frontend/src/services/apiClient.js`, `frontend/src/hooks/`, `frontend/src/pages/`
