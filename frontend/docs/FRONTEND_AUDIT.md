# Frontend Repository Audit

**Audit date:** 2026-11-02
**Repository:** `FerLpz55/PayPalAIHackathon-`
**Audited checkout:** `main` at `a45a1c3` (`feat(backend): implementa backend DDD con FastAPI, PostgreSQL y adaptadores`)
**Scope:** Read-only application audit. This document and `IMPLEMENTATION_ROADMAP.md` are the only intended additions.

> **Note (2026-11-04):** The root `PRODUCT.md` and `REQUIREMENTS.md` were removed during repository cleanup. References to them below describe the audited commit `a45a1c3`, not the current tree.

## Executive summary

The frontend is a responsive React 19/Vite demonstration with workshop and customer hash routes. Its interactive quote, order, receipt, and payment state is handled by `frontend/src/services/mockApi.js` and browser `localStorage`; there are no HTTP calls from `frontend/src`. A proposed contract exists in `frontend/docs/API_CONTRACT.md`.

The checked-in backend has moved beyond the older root `BACKENDREADME.md` and `PRODUCT.md` claims: FastAPI routers and use cases for quote, order, and payment flows are present, in addition to health. Backend documentation says PostgreSQL, AI, and PayPal need environment configuration; backend `.env.example` is a template, not evidence of a deployed/usable service. The front-end contract is broadly similar but has discrepancies that need reconciliation against backend schemas/OpenAPI before integration. Therefore interface work is actionable now, but production-like flow completion depends on backend/API agreement, reachable configured services, auth/customer-link delivery, and test credentials.

No issue descriptions, acceptance criteria, status, assignees, or dependency links could be verified in GitHub during this audit. The issue numbers and titles in the request are treated as scope labels only. The matrix separates requested-title interpretation from repository evidence; confirm issue bodies with the team before treating inferred criteria as authoritative.

## Repository and Git state

- Local checkout is nested at `PayPalAIHackathon-` inside the supplied workspace.
- Git reports `main...origin/main`, clean working tree, and both refs at `a45a1c3`; `origin/HEAD` points to `origin/main`.
- The checkout includes backend/database files as well as frontend files. No other local branches were reported by `git branch --all`.
- Git required a per-command `safe.directory` override because the checkout's Windows owner SID differs from the current process. No global Git configuration was changed.
- No dependencies were installed; no tests/build/lint were run (audit-only request).
- No frontend test/spec files or test script were found. Existing test files are backend Python tests and a SQL schema test.

## Evidence and confidence

“Confirmed” means observed in this checkout or its tracked documentation. “Proposed” means described only by a contract/requirements document. “Unavailable” means external issue/release/runtime evidence was not accessible.

| Area | Confirmed repository state | Confidence / limitation |
|---|---|---|
| Product requirements | `REQUIREMENTS.md` defines customer quote generation/review, PayPal checkout, order dashboard, persistence, and security constraints. | Confirmed as requirements, not implementation. |
| Root/product documentation | Root `BACKENDREADME.md` and `PRODUCT.md` say backend only has health and business integrations are pending. | Stale relative to actual backend router source at this commit. |
| Backend | `Backend/src/tallerclaro/main.py` includes health, quotes, orders, and payments routers. Router source implements their HTTP handlers. | Confirmed source implementation; no claim of deployed services or production readiness. |
| Backend integrations | Backend README and `.env.example` document database/AI/PayPal configuration; adapter/config code exists. | Configuration/deployment values are not present in the frontend and were not tested. |
| API contract | `frontend/docs/API_CONTRACT.md` proposes quote/order/payment endpoints, response shapes, auth, and error format. | Proposed contract; validate field names/statuses against backend Pydantic schemas/OpenAPI. |
| Frontend data | `mockApi.js` seeds local orders and persists state under `tallerclaro.demo.v1`; mutation methods are local. | Confirmed. This is demo state, not server persistence. |
| Frontend integration | No `fetch`/Axios/network client use appears in `frontend/src`; `VITE_API_BASE_URL` appears only as contract guidance. | Confirmed by source search. |
| Responsive CSS | `app.css` has breakpoints at 1100, 760, 390px, a short-landscape rule, and reduced-motion handling. | Confirmed CSS rules; no visual/device testing performed. |
| Accessibility | Some labels, `sr-only`, `role=img`/aria labels, and focus styling exist. | Partial evidence only; no WCAG audit or assistive-technology testing. |
| GitHub issues | Direct API issue URLs were inaccessible to the web tool; web search did not return repository issue content; no GitHub connector was available. | Issue criteria/status/dependency graph unverified. |

## Frontend structure and behavior

- `frontend/src/App.jsx` switches among dashboard, orders, quotes, receipts, accounting, customer request, quote review, tracking, and order detail screens.
- `frontend/src/hooks/useHashRoute.js` implements hash navigation. `useDemoData.js` loads and mutates the local mock service.
- `frontend/src/services/mockApi.js` owns seeded sample data and local operations: list/get order, quote creation, quote approval, payment simulation, status update, receipt record, and reset.
- `frontend/src/hooks/useQuoteRequest.js` and `useSpeechInput.js` support the sample request form; no AI service call is made.
- `QuoteReviewPage.jsx` shows line items and deposit/balance examples; approval and payment call local mock methods. A “Pay with PayPal” presentation is not a PayPal SDK/checkout integration.
- `OrderTrackingPage.jsx`, receipts, and accounting display demo/local records. Receipt handling records file metadata/name, not file content upload.
- Workshop order status changes persist only through local mock data. No customer/workshop authentication UI or API credentials flow was found.
- `frontend/package.json` has `dev`, `build`, `lint`, and `preview` scripts; dependencies are React/React DOM and Vite toolchain. There is no test script or test dependency.
- No frontend `.env*` file was found. Vite config has no API proxy or configured API origin.

## Routes

| Hash route | Page |
|---|---|
| `#/dashboard` | Dashboard |
| `#/orders` | Orders list |
| `#/quotes` | Quotes overview |
| `#/receipts` | Receipt list/upload-name demo |
| `#/accounting` | Illustrative accounting |
| `#/customer/new` | Customer request form |
| `#/customer/quote` | Quote review and demo approval |
| `#/customer/tracking` | Customer progress and demo payment view |
| `#/order/:id` | Workshop order detail/status editor |

Routes are client-side hashes; route availability does not establish that workflows meet backend acceptance criteria.

## Backend contract and integration gaps

The current backend source exposes these route groups under `/api`: `GET /health`; `POST/GET /quotes`, `POST /quotes/{id}/generate|approve|reject`; `GET /orders`, `GET/PATCH /orders/{id}`; `POST /orders/{id}/payments`; and `POST/GET /payments/{id}`, with the corresponding auth dependencies visible in routers. Backend README documents workshop Basic Auth and customer `X-Customer-Token` requirements for specified order/payment operations.

Before connecting the client:

1. Compare `frontend/docs/API_CONTRACT.md` with the checked-in Pydantic request/response schemas and live OpenAPI. The contract examples are not proof of exact wire compatibility.
2. Agree how the customer obtains and retains the required link token; do not put a shared workshop Basic Auth secret in browser code. Current quote/customer navigation has no token handling.
3. Confirm CORS/origin policy, API base URL setup, deployment/reachability, and sanitized error shape.
4. Confirm that database migrations are applied and backend is configured for its intended environment. Code presence alone does not prove persistence is available.
5. Confirm PayPal Sandbox and AI provider credentials/configuration outside the frontend. Never place provider secrets in `VITE_*` variables.
6. Resolve data mapping: local IDs/statuses/fields (`quote_sent`, `ready_to_finish`, `amount`, `paid`, camelCase) differ from proposed API statuses/fields (`pending`, `in_progress`, `total`, `paid_amount`, snake_case). Payment status must remain separate from production status.
7. Determine how receipt upload and customer-facing order tracking are supported; the proposed API contract currently does not define receipt endpoints or a public tracking lookup/link-token issuance flow.

## Issue analysis (criteria are provisional)

Because GitHub issue bodies were unavailable, the following acceptance points are inferred from the requested titles and `REQUIREMENTS.md`; they must not be reported as official issue acceptance criteria.

| Issue | Provisional acceptance focus from title/requirements | Current evidence and status |
|---|---|---|
| #15 Quote review and approval | Show validated quote detail and itemized total; approve/reject; pass server-authoritative quote/order onward. | Quote review UI and local approval exist. No AI-generated/validated estimate, server persistence, reject UI, or authoritative handoff. Partial demo only. |
| #16 Dashboard and order management | List persisted orders, show status/details, persist authorized status updates. | Dashboard/list/detail and local status updates exist. API routes exist in backend source, but frontend is not connected and no auth/persistence acceptance is met. Partial demo only. |
| #18 PayPal checkout and confirmation | Create checkout for server-calculated amount; handle approve/cancel/failure; capture/verify server-side; show verified result. | UI simulates payments locally. Backend payment endpoints and adapter code exist, but provider config/runtime and UI integration are unverified. Not implemented end-to-end. |
| #20 Customer navigation and order tracking | Navigate quote-to-payment-to-tracking, resolve customer order securely, show server-backed progress/payment. | Customer hash pages and local journey exist. No link-token issuance/use, backend reads, or verified payment status. Partial demo only. |
| #21 Accessibility and responsive design | Usable responsive views and accessible keyboard/screen-reader interaction. | Responsive rules and several semantic/accessibility affordances exist. No systematic WCAG/manual audit or automated accessibility tests were found. Partial baseline only. |
| #22 Demo separation and frontend documentation | Make demo mode explicit and explain setup, routes, limitations, and integration boundary. | Demo labels and docs exist in root/frontend README and components. Potential contradiction/staleness: root README claims only health endpoint, whereas backend source now includes business routes. No distinct runtime mode selector or backend-connected client exists. Partial documentation/demo separation. |
| #19 and #23 Shared tasks | Shared integration coordination/delivery; exact work split unclear without issue body. | Cannot confirm official shared scope, assignees, or dependency links. Frontend-owned contribution likely API client/data mapping, route/UI integration, accessibility verification, and frontend docs; coordinate schema/auth/error contracts with backend owner. |

## OWASP Top 10:2025 frontend-focused review

This is a source-level checklist, not a penetration test or claim of backend security. OWASP currently identifies the 2025 edition as the latest released Top 10. The frontend's demo-only behavior reduces immediate payment exposure but does not itself secure a future connected flow.

| Category | Frontend evidence / risk | Frontend follow-up |
|---|---|---|
| A01 Broken Access Control | No client auth/session or route permissions found; UI visibility is not authorization. API workshop operations require server enforcement. | Treat server authorization as authoritative; avoid exposing workshop credentials; test object-level/customer token scoping with backend. |
| A02 Security Misconfiguration | No frontend API origin/CORS/security-header setup shown. | Agree production origins, CSP/security headers, HTTPS, safe error display, and deployment config with platform/backend. |
| A03 Software Supply Chain Failures | Lockfile exists; no audit/SCA evidence or security CI was inspected. | Establish dependency/license/vulnerability review and CI policy before release; do not infer package safety from lockfile. |
| A04 Cryptographic Failures | No secrets found in client source; future token handling/storage policy is unspecified. | Never ship API/provider secrets in bundle; use HTTPS and minimize persistence of customer tokens/PII. Assess browser storage threat model. |
| A05 Injection | React renders user-visible data; no explicit dangerous HTML sink found in reviewed pages. | Preserve escaped rendering; avoid `dangerouslySetInnerHTML`; validate untrusted values at server and safely render backend errors. |
| A06 Insecure Design | Quote/payment demo concepts can suggest transitions that are not verified; local simulation is visibly labeled in key paths. | Keep quote approval, payment verification, and production status distinct; amount/status authority stays server-side. Threat-model link access and replay/idempotency with backend. |
| A07 Authentication Failures | No login/token workflow in client. Backend describes Basic Auth and customer token dependencies. | Do not implement shared Basic Auth in public browser code; define appropriate session/link-token issuance, expiry, revocation, and failure handling. |
| A08 Software or Data Integrity Failures | Demo records are mutable localStorage; no server integrity assurance. | Treat browser state as untrusted display cache only; verify all amount/status decisions server-side; validate API responses. |
| A09 Security Logging & Alerting Failures | No client security logging/alerting evidence. | Avoid logging tokens/PII; rely on backend security audit events and monitored operational alerts. Client telemetry should be privacy-limited. |
| A10 Mishandling of Exceptional Conditions | `mutate` paths and promise flows exist; error handling is not comprehensively verified, some component handlers set busy state around awaited mutation. | Test network timeout, malformed response, 401/403/404/409/422/503, cancellation, duplicate click, and offline cases; ensure busy state resets and actionable non-sensitive errors appear. |

## Files reviewed

Root: `BACKENDREADME.md`, `REQUIREMENTS.md`, `PRODUCT.md`, backend README and architecture plan, database README/schema/migration/seeds. Frontend: `package.json`, lockfile presence, Vite/ESLint configuration, frontend README, `docs/API_CONTRACT.md`, `docs/DESIGN_REFERENCE.md`, `src/App.jsx`, all files under `src/components`, `src/pages`, `src/hooks`, `src/services`, `src/styles`, `src/utils`, and `src/main.jsx`. Backend source was read to establish actual router and configuration scope. No code changes were made.

## External references

- [OWASP Top 10:2025 introduction and category list](https://top10.owasp.org/2025/0x00_2025-Introduction/)
- GitHub issue content was not retrievable during the audit; issue criteria and status remain unverified.
