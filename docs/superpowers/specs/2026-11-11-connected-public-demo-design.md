# Connected Public Demo Design

## Intent

The production frontend must open directly on the public customer quote flow without showing the workshop login. That public journey must use the deployed FastAPI backend, PostgreSQL on Supabase, the configured AI provider, Channel3, and PayPal Sandbox.

## Goals

- Make the empty/root URL resolve to `#/customer/new` behavior.
- Keep `#/dashboard` and other workshop routes protected by the existing cookie session login.
- Preserve the existing three-mode contract: `demo` remains local mock data, `real` uses the backend, and an unconfigured build exposes neither.
- Build production with `VITE_APP_MODE=real` and `VITE_API_BASE_URL=https://tallerclaro-backend.vercel.app`.
- Prove with a browser test that the public flow invokes quote creation, AI generation, Channel3-backed product retrieval, quote approval, and PayPal payment creation without requesting a workshop session.

## Non-goals

- Do not bypass backend authentication on workshop routes.
- Do not call providers directly from the browser or expose provider secrets through `VITE_*` variables.
- Do not mix local mock records with backend records or silently fall back to mocks.
- Do not apply database migrations or seed production data as part of this frontend change.

## Approach

Keep the existing connected customer flow and change only the public entry route and customer header links. The backend already owns AI generation, Channel3 lookup, PayPal order creation, customer-token authorization, and database persistence; duplicating those integrations in the frontend would weaken the architecture. A mocked HTTP browser test will pin the full UI wiring, then the deployed frontend will be built in `real` mode and smoke-tested against the live backend.

## Constraints

- Frontend package commands use `pnpm` only.
- Provider credentials remain backend-only.
- PayPal status is authoritative only after backend reconciliation.
- Live provider and database verification must be reported separately from mocked browser verification.
