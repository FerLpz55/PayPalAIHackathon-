# Connected Public Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open the deployed site on the public connected quote journey and expose the existing backend-driven AI, Channel3, and PayPal flows without an initial workshop login.

**Architecture:** Keep `demo`, `real`, and `unconfigured` behavior separate. Change the hash router's empty-path default to the public customer request route, retain authentication on explicit workshop routes, and deploy the frontend with `VITE_APP_MODE=real` so all integrations continue through FastAPI.

**Tech Stack:** React 19, Vite 8, Vitest, Playwright, FastAPI, Vercel CLI

**Spec:** `docs/superpowers/specs/2026-11-11-connected-public-demo-design.md`

## Global Constraints

- Use `pnpm` only in `frontend/`.
- Never expose database, AI, Channel3, PayPal, workshop-password, or customer-token secrets in `VITE_*` variables.
- Do not add a mock fallback to connected mode.
- Keep workshop routes protected by the existing cookie/CSRF session.
- Do not write to or migrate the deployed PostgreSQL database during automated verification.

## Review Focus

- Empty URL must show the public request form and must not request `/api/auth/session`.
- Explicit `#/dashboard` must still enter the protected workshop-session flow.
- A customer token returned during quote creation must authorize every subsequent customer request.
- Channel3 results with missing price or unsafe URLs must remain non-actionable or unlinked.
- PayPal checkout must use only the backend-provided safe approval URL and never mark payment complete from the browser alone.

---

### Task 1: Pin the connected public journey

**Files:**
- Create: `frontend/e2e/public-connected-demo.spec.js`
- Modify: `frontend/src/hooks/useHashRoute.js`
- Modify: `frontend/src/components/layout/CustomerHeader.jsx`

**Interfaces:**
- Consumes: existing `apiClient.createQuote`, `apiClient.getCustomerContext`, `apiClient.getQuote`, `apiClient.approveQuote`, and `apiClient.createOrderPayment` methods.
- Produces: empty hash resolves to `customer/new`; customer header links resolve to `#/customer/new`.

- [x] **Step 1: Write the failing browser test**

Create `public-connected-demo.spec.js` with a route-backed API fixture. Assert that `/` shows “What would you like us to make?”, never calls `/api/auth/session`, submits a quote through `POST /api/quotes` and `POST /api/quotes/{id}/generate`, renders a Channel3 product from `GET /api/quotes/{id}`, approves through `POST /api/quotes/{id}/approve`, and renders a PayPal checkout created through `POST /api/orders/{id}/payments`. Add a separate assertion that visiting `#/dashboard` requests the workshop session and shows the login after a `401`.

- [x] **Step 2: Run the browser test and verify RED**

Run: `pnpm exec playwright test e2e/public-connected-demo.spec.js`

Expected: the root-route assertion fails because the current empty hash resolves to `dashboard` and requests the workshop session.

- [x] **Step 3: Implement the route change**

Change `readLocation()` in `useHashRoute.js` so an empty path resolves to `customer/new`. Change both customer-header dashboard links to `#/customer/new`. Do not alter explicit workshop routes or authentication.

- [x] **Step 4: Run the focused test and full frontend verification**

Run: `pnpm exec playwright test e2e/public-connected-demo.spec.js`

Expected: PASS.

Run: `pnpm run test && pnpm run lint && pnpm run build && pnpm run test:e2e`

Expected: all commands PASS without warnings introduced by the change.

### Task 2: Restore the production connection and verify deployment

**Files:**
- Modify externally: Vercel Production environment for `tallerclaro-frontend`
- No repository file should contain production credentials.

**Interfaces:**
- Consumes: `VITE_API_BASE_URL=https://tallerclaro-backend.vercel.app` and the deployed backend health/API routes.
- Produces: production build with `VITE_APP_MODE=real` at `https://tallerclaro-frontend.vercel.app`.

- [ ] **Step 1: Verify backend liveness and production variable names**

Confirm `GET https://tallerclaro-backend.vercel.app/api/health` returns `200`, and confirm the frontend production environment contains `VITE_API_BASE_URL` without printing secret values.

- [ ] **Step 2: Set connected production mode and deploy**

Set `VITE_APP_MODE=real` for Production and run the Vercel production deployment from `frontend/`.

- [ ] **Step 3: Smoke-test the deployed entry route**

Open the production frontend without a hash and assert the public request form is visible and the workshop login is absent. Confirm explicit `#/dashboard` remains protected.

- [ ] **Step 4: Report verification boundaries**

Report mocked end-to-end coverage separately from live health/UI checks. Do not claim live AI, Channel3, PayPal, or PostgreSQL success unless the real customer flow was exercised and its provider-backed results were observed.

- [ ] **Step 5: Commit and push**

Commit the source/tests/docs with a focused message and push `main` only after verification passes.
