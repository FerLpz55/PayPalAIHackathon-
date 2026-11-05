# Frontend Implementation Roadmap

**Prepared:** 2026-11-02 from local checkout `main` at `a45a1c3`.

> **Historical roadmap:** Backend and frontend changes since this checkout
> supersede several blockers below, including token issuance, CORS, bcrypt
> authentication and configurable PayPal return URLs. This is not a current
> task list. Refer to [the frontend guide](../README.md) and [the backend
> guide](../../Backend/BACKENDREADME.md) for current capabilities and gaps.
**Purpose:** Sequence frontend-owned implementation for issues #15, #16, #18, #20, #21, #22 and frontend contributions to #19/#23. The exact GitHub issue bodies and dependency graph were unavailable; priorities below are a recommended technical sequence, not official issue acceptance criteria.

## Delivery principles

- Keep the demo usable and clearly distinguished from server-backed behavior until each integration is actually connected and verified.
- Do not trust browser totals, payment state, localStorage, or client route visibility as authority.
- Do not embed PayPal/AI secrets or shared workshop credentials in Vite client variables.
- Keep payment state separate from order fulfillment state.
- Route presence in source does not prove that database, AI, PayPal, CORS, or deployment is usable.
- Do not represent an issue as complete because its screen exists. Completion must follow issue-specific acceptance evidence and integrated verification.

## Recommended execution order

### 0. Align shared contracts (#19/#23) — integration gate

The source review is documented in [API_CONTRACT.md](./API_CONTRACT.md). Existing route handlers establish quote/order/payment wire shapes, but integration is blocked by missing customer token issuance and tracking reads, unresolved workshop browser authentication, payment token object scoping, absent CORS evidence, inconsistent service error status mapping, and unconfigured/unverified runtime dependencies. The PayPal adapter also has hardcoded placeholder return/cancel URLs.

**Frontend can do now:** derive UI field/status needs from the API inventory; produce a mapping proposal; identify expected loading/error/empty states; coordinate questions with backend owners. Preserve the existing local demo behavior and labels.

**Backend/team answers required before network wiring:** API origin/version/CORS; auth and customer-link issuance/use; quote actor/visibility and AI follow-up behavior; order customer/display fields and post-deposit transition; error envelope/status guarantees; PayPal return/cancel flow; receipt scope; and a configured integration environment. The payment token's verified identity must be enforced against the requested resource before customer payment APIs are trusted.

**Exit evidence:** backend-approved request/response/error examples matching OpenAPI; secure resource-scoped auth contract; configured reachable non-production API; confirmation that external dependencies and migrations are ready. This is a gate before connecting feature screens, not just a parallel documentation task.

### 1. Accessibility and responsive audit/fixes (#21) — independent

Review all hash routes at narrow and wide viewports, including short landscape. Verify keyboard navigation, visible focus, heading order, form labels/errors, button names, dialogs/focus return, mobile navigation state, table overflow, color contrast, zoom/reflow, reduced motion, and screen-reader output. Correct frontend issues without waiting for the backend.

**Verification:** repeatable viewport/keyboard checklist and results; test representative screens with an accessibility scanner/manual screen reader. Do not claim conformance from CSS breakpoints alone.

### 2. Demo separation and documentation (#22) — frontend phase implemented

The frontend documentation and labels now state that business workflows remain local demos. The checked-in backend does contain quote/order/payment route handlers, but the frontend does not call them and their runtime availability is unverified. Receipt selection stores only a file name, and accounting figures are illustrative. See [DEMO_VS_REAL_FUNCTIONALITY.md](./DEMO_VS_REAL_FUNCTIONALITY.md) for the evidence matrix.

**Remaining:** root README and backend setup documentation should be reconciled by their owners where they describe backend route scope; backend environment/reachability and all API/auth contracts still require team confirmation. Do not select a connected mode or add a mock fallback until the backend integration gate is satisfied.

**Verification:** frontend README has run instructions, route table, browser demo-data/reset behavior, classifications, and backend gate. Key page copy and receipt behavior were checked against `mockApi` call sites. Live checkout, AI pricing, file upload, or server persistence are not claimed.

### 3. Contract-safe frontend preparation — independent, no network behavior

Prepare display-field mapping and component requirements from the verified contract. Separate quote ID from order ID and payment status from fulfillment status in UI modeling. Design presentation states for loading, empty, validation, unauthorized, conflict, unavailable dependency, cancelled payment, and retry. Do not add a service client, simulated API endpoint, or silent mock fallback while auth, resource access, error behavior, and deployment remain unresolved.

**Verification:** review UI mapping against API_CONTRACT and confirm demo labels remain truthful. Keep current local behavior explicit.

### 4. Frontend API client foundation — blocked by contract gate

After gate 0, introduce a replaceable HTTP service layer rather than placing requests in page components. Configure an API base URL only after deployment ownership is confirmed; centralize JSON/error parsing, request timeout/cancellation, and snake_case/authoritative-state mapping. Do not embed workshop Basic credentials or provider secrets. Do not silently fall back to mock data after API failure.

**Blocked by:** base URL/CORS; agreed auth/token; uniform error semantics; API schema/version; reachable configured backend.

**Verification:** actual client tests for successful payloads, empty results, malformed payloads, validation/auth/conflict/service errors, and timeout. These must exercise the HTTP client and must not create mock endpoints.

### 5. Dashboard and order management (#16)

Connect list/detail/status UI after the workshop auth contract and order payload needs are resolved. Existing routes require workshop Basic Auth, which is not safe to hardcode in a public browser bundle; source currently compares password with a literal placeholder. Order response lacks customer/project fields used by demo screens. Use backend transitions and keep payment status separate.

**Blocked by:** secure workshop auth; API origin/CORS; database/config readiness; agreed customer/project data; verified status transitions.

**Verification:** authorized/unauthorized, persistence after reload, status validation, payment/fulfillment separation, and failures against configured API; responsive/keyboard checks.

### 6. Quote request, review, and approval (#15)

Connect create/generate/retrieve/approve/reject only after actor and visibility are agreed. Backend currently requires `carpenter_id`, splits create and generate, returns a `needs_information` state without its actual missing fields, and approval returns an Order but no customer token. Preserve server totals and handle provider errors per the agreed response contract.

**Blocked by:** AI configuration; correct preservation of missing info/assumptions; customer/workshop approval policy; persistence; customer access/link issuance; stable errors.

**Verification:** valid/incomplete/provider unavailable, idempotent approval, reload, tampered amount, reject, and access policy.

### 7. Customer navigation and order tracking (#20)

Wait for a customer-safe order/quote read endpoint and a defined link-token issuance/delivery/expiry/revocation flow. Existing payment token checks are not demonstrably scoped to requested payment/order, and existing order detail read requires workshop Basic Auth. Do not use a guessable numeric ID or local route guard as customer authorization.

**Blocked by:** token issuance and resource authorization, read endpoint and customer-facing fields, CORS/deployment, verified payment/order read semantics.

**Verification:** valid/expired/revoked/wrong-resource token, deep-link/reload, unknown resource, and payment-versus-fulfillment statuses.

### 8. PayPal checkout and confirmation (#18)

Use the server to create payment intent from an approved order, send the customer through the agreed PayPal Sandbox approval flow, handle cancellation/failure/return, capture via backend, and retrieve verified status before showing success. Current adapter has hardcoded example.com return/cancel URLs; the UI cannot complete a deployable redirect flow without configuration. Prevent duplicate submissions and follow server retry/idempotency semantics.

**Blocked by:** configured PayPal Sandbox backend; configurable return/cancel contract; secure token scope; customer checkout flow; verified persistence and response semantics.

**Verification:** Sandbox approval, cancel, provider failure, capture success/failure, repeated capture/intent, amount integrity, pending return state, and refresh after verified capture.

### 9. Integration hardening and shared acceptance (#19/#23)

Run agreed frontend checks against the configured backend, add approved API/accessibility coverage, inspect browser network traffic for secrets/PII, verify errors/keyboard/responsive flows, and update documentation with demonstrated capabilities only. Shared completion needs frontend and backend evidence.

## Dependency summary

| Workstream | Can begin independently | Requires backend/team availability |
|---|---|---|
| #21 accessibility/responsive | Full source audit and UI fixes | Integrated auth/API-error states need connected API |
| #22 demo separation/docs | Correct descriptions of demo behavior and source-level backend status | Agreed deployment/setup and proven integration features |
| #19/#23 coordination | Field/status inventory and contract questions | OpenAPI/error/auth/CORS/token decisions and shared ownership |
| API client foundation | UI data mapping and service requirements only | Agreed schema/version, origin/CORS, secure auth, error contract, reachable API |
| #16 dashboard | UI states and status mapping proposal | Safe workshop auth, order display fields, persistence, reachable API |
| #15 quote review | UI state/error design | Correct missing-info payload, actor policy, persistence, quote/customer access |
| #20 tracking | Route and state UX design | Customer link issuance/scoping and customer order-read endpoint |
| #18 checkout | UI state/error design; preserve truthful demo copy | Configured PayPal, return/cancel URLs, resource-scoped token, verified capture |

## Definition of done for frontend work

Use authoritative issue acceptance criteria once available. Record separately: code delivered, test evidence, backend prerequisite evidence, and remaining limitation. A route/component or simulated browser state alone does not satisfy persistence, access control, AI, or payment criteria.
