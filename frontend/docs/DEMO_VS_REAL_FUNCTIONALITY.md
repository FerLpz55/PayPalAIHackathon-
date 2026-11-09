# Demo Versus Real Functionality

**Evidence date:** 2026-11-03

> **Historical matrix:** Some rows below describe an earlier implementation
> (including claims that no HTTP client exists). The current transport is
> `src/services/http.js`, called through `apiClient.js`. Use [the frontend
> guide](../README.md) for current DEMO/REAL behavior and authorization limits,
> and [the backend guide](../../Backend/BACKENDREADME.md) for server capabilities.
> Source integration still does not establish a working deployed flow.
> **Update 2026-11-09 (phase F):** workshop auth is now an `HttpOnly` cookie
> session plus CSRF from `POST /api/auth/login`; customer links are recovered with
> `GET /api/customer/context`; payments use `sync`/`cancel` instead of `capture`.
> Rows below are annotated where they changed.
**Scope:** Current frontend implementation compared with checked-in backend source. This is a source review; backend route availability, deployment, configuration, and production readiness were not tested.

## Classification rules

- **REAL (source integrated; runtime unverified)** means the frontend calls the configured backend and presents its response. This label does not claim deployment, availability, or E2E success.
- **DEMO** means the current frontend action uses fixed/sample data, local state, local storage, simulated timing, or browser-only behavior.
- **PARTIAL** means a limited user-facing capability works but the requested end-to-end feature is incomplete. It does not imply a backend integration.
- **NOT IMPLEMENTED** means the listed integration or capability is absent from the frontend.

Backend route handlers can exist without being operational. They are called out as dependencies, not evidence of a real frontend feature.

## Feature matrix

| Feature | Current Status | Evidence | Demo Behavior | Backend Dependency | Next Step |
|---|---|---|---|---|---|
| Customer request submission | **PARTIAL** | `RequestForm.jsx` calls `apiClient.createQuote` in REAL mode and uses `mockApi` only in explicit DEMO mode. | DEMO creates a fixed example quote locally. | REAL requires backend API origin, CORS, AI/database config, and a valid backend response. | Validate with configured backend and AI service. |
| AI quote generation | **DEMO** | `mockApi.createQuote` supplies fixed project, measurements, items, price, deposit, and balance. There is no AI or HTTP client in `frontend/src`. Backend has `POST /api/quotes/{id}/generate` in source. | A fixed illustrative quote appears after request submission; amount is not calculated by AI or a pricing service. | AI adapter configuration/runtime, output schema, missing-information follow-up, and error semantics need confirmation. The route does not currently return usable assumptions/missing-info details per API contract review. | Do not present demo estimate as AI-produced. Integrate only after backend response behavior and configured environment are verified. |
| Quote review and approval | **PARTIAL** | REAL uses backend quote GET, approve, and `/api/quotes/{id}/generate`; DEMO uses local state. | DEMO quote totals are illustrative only. | Backend AI output, order persistence, and deployment remain unverified. | Test with backend/AI configuration. |
| Customer order tracking | **PARTIAL** | REAL retrieves quote and order data with the saved customer token; DEMO uses local sample data. | DEMO status and payment figures are simulated. | Customer token expiry/recovery and backend runtime remain unverified. | Exercise scoped read against backend. |
| Workshop dashboard | **PARTIAL** | REAL reads `/api/orders` after the cookie session is confirmed by `GET /api/auth/session`; DEMO reads `mockApi.listOrders`. Missing API configuration shows an empty configuration state. | Seeded sample customers/orders are shown only when `VITE_APP_MODE=demo`. | Backend availability and a production workshop session flow remain runtime-unverified. The client no longer stores or sends `taller:demo-password`. | Test live data with a configured backend and `SameSite`/CORS matching the deployment topology. |
| Order management | **PARTIAL** | REAL order list/detail/status calls require the workshop cookie session; customer screens read through `GET /api/customer/context`. DEMO uses local data. | Status edits in DEMO affect only local state. | Workshop session, CSRF and runtime behavior remain unverified. | Test backend-backed order updates. |
| PayPal checkout and confirmation | **PARTIAL; runtime unverified** | REAL creates an idempotent attempt, redirects to the returned Sandbox approval URL, reconciles with `POST /api/payments/{id}/sync` (capture only on PayPal `APPROVED`) and closes attempts with `POST /api/payments/{id}/cancel`; returns also recover via the client link. DEMO is labeled and local only. | No PayPal activity occurs in DEMO. | Return/cancel URLs are configurable on the backend; webhook reconciliation and Sandbox runtime were not exercised. | Configure backend return/cancel URLs and validate a real Sandbox round trip plus webhook delivery. |
| Receipts | **DEMO** | `ReceiptsPage.jsx` calls `mockApi.addReceipt`; the service stores `file.name`, an illustrative amount/status record, and no file bytes. | Selecting a file adds only its name to local state. Seeded entries and totals are examples; no upload, review, or official receipt is produced. | No receipt upload/list/review/verification route was found in checked-in handlers. Storage, file limits/type validation, malware handling, amount review, and authorization need backend design. | Keep the selection-only disclosure. Do not describe selected files as uploaded; define secure upload and review contract before implementation. |
| Accounting and financial reports | **DEMO** | `AccountingPage.jsx` sums local `order.paid`/`spent` values and includes hard-coded monthly values. | Renders illustrative payment/expense totals and a sample chart. It is not a ledger, official statement, tax report, or verified financial data. | No accounting/report aggregate endpoint was found. Order/payment financial semantics and verified data source need agreement. | Keep â€œillustrative/demoâ€ labels; implement reports only from agreed server-verified data and accounting rules. |
| Browser speech-to-text | **PARTIAL** | `hooks/useSpeechInput.js` uses `SpeechRecognition`/`webkitSpeechRecognition` when exposed by the browser and falls back to text input. | Transcribes speech into the request field; unsupported browsers can type. It does not understand the request or generate a quote. | No backend dependency for browser transcription; AI interpretation remains a separate unconnected capability. | Retain text fallback and avoid calling transcription â€œAI quote generation.â€ |
| Frontend API client / mode selection | **PARTIAL** | `apiClient.js` separates explicit DEMO, configured REAL, and unconfigured modes; `http.js` sends cookies with `credentials: 'include'` and the CSRF header. | Unconfigured mode hides sample data; backend errors do not fall back to fixtures. | Backend origin, CORS with credentials, cookie `SameSite` and runtime remain environment-dependent. | Validate against the deployed backend. |

## Backend route evidence versus frontend integration

The checked-in FastAPI app includes `/api/health`, quote, order, and payment routers. Their request/response fields, status values, authentication dependencies, and known gaps are documented in [API_CONTRACT.md](./API_CONTRACT.md). These are **verified in source**, not runtime-tested. DEMO invokes `mockApi`; REAL calls the configured business routes and shows connection errors without fixture fallback.

The root `BACKENDREADME.md` still says the backend exposes only a health endpoint. That statement conflicts with the checked-in route handlers; update it through the repository documentation owner. The route source still does not establish deployed or operational capability.

## Demo data behavior

- `src/services/mockApi.js` loads seeded examples and current state into module memory. Mutations serialize state to the `tallerclaro.demo.v1` local storage key.
- The seed contains example names, email addresses, order identifiers, amounts, statuses, receipts, and payment values. Treat all of them as fabricated demonstration records.
- A customer request persists a fixed illustrative quote; approval creates a local order; simulated deposit/balance actions update local payment fields; order status edits and receipt-name entries are local.
- Receipt file contents are not read, uploaded, or stored. Only the chosen file name is added to local state.
- Accounting derives some values from demo orders and includes hard-coded monthly figures.
- To restore the seed, remove `tallerclaro.demo.v1` from browser storage and reload. Do not use the browser store as authoritative data.

## Integration blockers to resolve with the backend team

1. Confirm a reachable non-production API origin, API version, CORS policy (with credentials), migrated database (migrations 005–008), and configured AI/PayPal services.
2. Confirm the workshop cookie session across the deployment topology: HTTPS, `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none` for Vercel→API, allowed `Origin`, and CSRF delivery. Never embed shared Basic Auth credentials in a public frontend bundle.
3. Confirm how client links are delivered, expired, revoked and scoped; reissue is workshop-only and revokes previous tokens.
4. Agree quote authorization, `carpenter_id`, generation follow-up for missing information, preservation of assumptions, and approve/reject actor semantics.
5. Define customer-facing tracking reads and the order display fields needed by the current dashboard/detail UI.
6. Confirm order status transitions after deposit capture and publish a stable error/status contract matching OpenAPI.
7. Configure PayPal return/cancel URLs and validate redirect, webhook and `sync`/`cancel` behavior, retry and idempotency against Sandbox.
8. Define whether receipt uploads and accounting reports are in scope, including data validation, storage, authorization, verified amount review, and official-document semantics.

See the unresolved questions and source-level route descriptions in [API_CONTRACT.md](./API_CONTRACT.md). No backend changes or routes are proposed by this feature matrix.
