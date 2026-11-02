# Demo Versus Real Functionality

**Evidence date:** 2026-11-02
**Scope:** Current frontend implementation compared with checked-in backend source. This is a source review; backend route availability, deployment, configuration, and production readiness were not tested.

## Classification rules

- **REAL** means the frontend feature calls a verified backend integration and presents its response. No current business workflow meets this definition.
- **DEMO** means the current frontend action uses fixed/sample data, local state, local storage, simulated timing, or browser-only behavior.
- **PARTIAL** means a limited user-facing capability works but the requested end-to-end feature is incomplete. It does not imply a backend integration.
- **NOT IMPLEMENTED** means the listed integration or capability is absent from the frontend.

Backend route handlers can exist without being operational. They are called out as dependencies, not evidence of a real frontend feature.

## Feature matrix

| Feature | Current Status | Evidence | Demo Behavior | Backend Dependency | Next Step |
|---|---|---|---|---|---|
| Customer request submission | **DEMO** | `src/hooks/useQuoteRequest.js` imports `mockApi`; `src/services/mockApi.js:createQuote` builds and stores a fixed quote. `RequestForm.jsx` has local field validation. | Text and optional browser speech input are accepted; submitting creates a fixed sample estimate in `tallerclaro.demo.v1`. | `POST /api/quotes` exists in source and accepts a different shape (`customer`, `carpenter_id`, `request`), but no frontend request is sent. Customer access/token handling and runtime DB are unresolved. | Keep copy explicit. After API origin, CORS, privacy/consent, carpenter ID, and customer authorization are agreed, map the form to the create contract. |
| AI quote generation | **DEMO** | `mockApi.createQuote` supplies fixed project, measurements, items, price, deposit, and balance. There is no AI or HTTP client in `frontend/src`. Backend has `POST /api/quotes/{id}/generate` in source. | A fixed illustrative quote appears after request submission; amount is not calculated by AI or a pricing service. | AI adapter configuration/runtime, output schema, missing-information follow-up, and error semantics need confirmation. The route does not currently return usable assumptions/missing-info details per API contract review. | Do not present demo estimate as AI-produced. Integrate only after backend response behavior and configured environment are verified. |
| Quote review and approval | **DEMO** | `QuoteReviewPage.jsx` reads the demo quote; `mockApi.approveQuote` changes local status and adds a local order. Backend has quote GET/approve/reject routes in source; none are called. | Customer can approve an example quote locally. The total cannot become payable or server-authoritative. | Quote visibility/actor policy, customer token issuance, persistence, approval idempotency, and link to resulting order must be agreed. | Preserve example labeling; map quote and order IDs separately after a secure customer contract exists. |
| Customer order tracking | **DEMO** | `OrderTrackingPage.jsx` derives an order from local quote/order arrays and `localStorage`. No customer read API call exists. | Displays sample status, receipt entries, and simulated payment summary from browser state. | No customer-authorized order/quote tracking read endpoint or link-token issuance route was found. Payment token resource scoping is unresolved. | Do not treat a guessable ID or hash route as authorization. Wait for token issuance and scoped customer read API. |
| Workshop dashboard | **DEMO** | `DashboardPage.jsx` derives active, awaiting-advance, in-production, delivered, and recent-order summaries from `orders` supplied by `App.jsx`; `useDemoData.js` reads `mockApi.listOrders`. Backend order list exists in source but is not called. | Seeded sample customers/orders and locally mutated statuses are shown. Summary figures are explicitly identified as demo data. | `GET /api/orders` requires workshop Basic Auth. A safe browser session/auth design, order display fields, CORS, persistence, and environment are unresolved. | Keep the Demo workspace indicator. Do not put shared Basic credentials in the bundle. |
| Order management | **DEMO** | `OrdersPage.jsx`, `OrderDetailPage.jsx`, `OrdersTable.jsx`, and `mockApi.updateStatus` operate on local demo data. No `fetch`/Axios integration exists. | Search covers order ID, customer, and project; status filter and date/amount sorting are local. Desktop uses an accessible table and narrow screens use order cards. Confirmed status edits allow `pending -> in_progress` and `paid -> in_progress`; delivery is disabled in the demo because the required backend-verified full payment cannot be established locally. Legacy demo-only statuses are read-only in this editor. The Accounting page can record a local note without changing order status or payment. | `GET/PATCH /api/orders/{id}` exists in source with workshop auth; customer/project display fields, payment/status semantics, and a safe browser auth flow remain unresolved. Backend route presence does not verify runtime availability. | Agree safe workshop auth and data mapping, then implement against persisted API responses without fallback to local fixtures. |
| PayPal checkout and confirmation | **DEMO** | `QuoteReviewPage.jsx` and `OrderTrackingPage.jsx` call `mockApi.simulatePayment`; it changes `paymentDemo`, paid amount, and local status. Backend payment routes are not called. | CTA explicitly simulates a deposit/balance; no PayPal checkout, request, charge, capture, or verified confirmation occurs. | Backend create/capture/payment routes exist in source, but runtime PayPal configuration, redirect/cancel flow, customer token issuance and object-level authorization, idempotency, and post-capture status are unresolved. | Keep simulation wording. Connect only after scoped authorization and a verified Sandbox round trip; never trust browser amount/status. |
| Receipts | **DEMO** | `ReceiptsPage.jsx` calls `mockApi.addReceipt`; the service stores `file.name`, an illustrative amount/status record, and no file bytes. | Selecting a file adds only its name to local state. Seeded entries and totals are examples; no upload, review, or official receipt is produced. | No receipt upload/list/review/verification route was found in checked-in handlers. Storage, file limits/type validation, malware handling, amount review, and authorization need backend design. | Keep the selection-only disclosure. Do not describe selected files as uploaded; define secure upload and review contract before implementation. |
| Accounting and financial reports | **DEMO** | `AccountingPage.jsx` sums local `order.paid`/`spent` values and includes hard-coded monthly values. | Renders illustrative payment/expense totals and a sample chart. It is not a ledger, official statement, tax report, or verified financial data. | No accounting/report aggregate endpoint was found. Order/payment financial semantics and verified data source need agreement. | Keep â€œillustrative/demoâ€ labels; implement reports only from agreed server-verified data and accounting rules. |
| Browser speech-to-text | **PARTIAL** | `hooks/useSpeechInput.js` uses `SpeechRecognition`/`webkitSpeechRecognition` when exposed by the browser and falls back to text input. | Transcribes speech into the request field; unsupported browsers can type. It does not understand the request or generate a quote. | No backend dependency for browser transcription; AI interpretation remains a separate unconnected capability. | Retain text fallback and avoid calling transcription â€œAI quote generation.â€ |
| Frontend API client / real integration mode | **NOT IMPLEMENTED** | `rg` source review found no `fetch`, Axios, XMLHttpRequest, API origin, or frontend environment configuration. `src/services/mockApi.js` is the only workflow service. | There is a single local demo workflow; there is no mode switch or silent mock fallback after API failure. | Backend origin/version, CORS, safe workshop auth, customer token delivery/scope, consistent errors, and reachable configured API remain unresolved. | Agree #19/#23 integration contracts and environment first; then create a separately named API client and explicit mode selection. |

## Backend route evidence versus frontend integration

The checked-in FastAPI app includes `/api/health`, quote, order, and payment routers. Their request/response fields, status values, authentication dependencies, and known gaps are documented in [API_CONTRACT.md](./API_CONTRACT.md). These are **verified in source**, not runtime-tested. The current frontend invokes only `mockApi` functions and does not contact `/api/health` or any business route.

The root `README.md` still says the backend exposes only a health endpoint. That statement conflicts with the checked-in route handlers; update it through the repository documentation owner. The route source still does not establish deployed or operational capability.

## Demo data behavior

- `src/services/mockApi.js` loads seeded examples and current state into module memory. Mutations serialize state to the `tallerclaro.demo.v1` local storage key.
- The seed contains example names, email addresses, order identifiers, amounts, statuses, receipts, and payment values. Treat all of them as fabricated demonstration records.
- A customer request persists a fixed illustrative quote; approval creates a local order; simulated deposit/balance actions update local payment fields; order status edits and receipt-name entries are local.
- Receipt file contents are not read, uploaded, or stored. Only the chosen file name is added to local state.
- Accounting derives some values from demo orders and includes hard-coded monthly figures.
- To restore the seed, remove `tallerclaro.demo.v1` from browser storage and reload. Do not use the browser store as authoritative data.

## Integration blockers to resolve with the backend team

1. Confirm a reachable non-production API origin, API version, CORS policy, migrated database, and configured AI/PayPal services.
2. Agree safe workshop browser authentication; never embed shared Basic Auth credentials in a public frontend bundle.
3. Define how customer tokens are issued, delivered, expired, revoked, and scoped to quote/order/payment reads and payment operations.
4. Agree quote authorization, `carpenter_id`, generation follow-up for missing information, preservation of assumptions, and approve/reject actor semantics.
5. Define customer-facing tracking reads and the order display fields needed by the current dashboard/detail UI.
6. Confirm order status transitions after deposit capture and publish a stable error/status contract matching OpenAPI.
7. Configure PayPal return/cancel URLs and agree redirect, capture, cancellation, retry, and idempotency behavior.
8. Define whether receipt uploads and accounting reports are in scope, including data validation, storage, authorization, verified amount review, and official-document semantics.

See the unresolved questions and source-level route descriptions in [API_CONTRACT.md](./API_CONTRACT.md). No backend changes or routes are proposed by this feature matrix.
