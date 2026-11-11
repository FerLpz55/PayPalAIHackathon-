# PayPal return and cancel URLs for issue #18

The customer application handles these hash routes:

- Return after approval: `https://<frontend-host>/<base-path>/#/customer/payment/return`
- Return after cancellation: `https://<frontend-host>/<base-path>/#/customer/payment/cancel`

For a local Vite run, the corresponding routes are `http://localhost:5173/#/customer/payment/return` and `http://localhost:5173/#/customer/payment/cancel`. PayPal Sandbox must be able to reach the configured frontend host; localhost is only useful for local navigation checks.

As of 2026-11-04, backend settings `TALLERCLARO_PAYPAL_RETURN_URL` and
`TALLERCLARO_PAYPAL_CANCEL_URL` feed `application_context` in
`Backend/src/tallerclaro/infrastructure/payment/paypal_processor.py`. Both must
be HTTPS URLs; invalid or missing values prevent startup when PayPal is enabled.
The local HTTP routes above are useful for navigation checks; use an HTTPS host
for checkout configuration. No frontend query parameter overrides these settings.
A complete PayPal Sandbox round trip remains unverified.

The PayPal Orders v2 approval link contains the PayPal order token as `token` (the checked-in adapter returns the approval link supplied by PayPal). The return page treats that value only as a consistency check against the `paypal_order_id` saved from the backend response. It never treats it as authentication or payment success. The customer token is never put in the URL. `PayerID` is not used by this REST Orders v2 flow.

On an approval return, the frontend reads the saved internal `payment_id`, calls `GET /api/payments/{payment_id}`, checks that the returned order and PayPal order IDs match the saved attempt, and requests capture only while the server reports `pending`. It then reads the payment again and displays success only if that matching backend record reports `completed`. On the cancellation route, the frontend only reads backend state; it does not request capture or mark the backend attempt cancelled.

The payment POST, GET, and capture routes all use `CustomerTokenDep`; the handlers derive the authorized quote ID and the payment use cases check that it belongs to the order. This is source-level authorization evidence, not a live authorization test. If browser storage is lost before return, the current API has no customer-scoped way to list or recover an order's pending payment attempts. The frontend cannot safely reconstruct that association from the PayPal URL token alone. Backend needs a customer-scoped reconciliation/read mechanism (or an idempotent create-payment request plus a way to retrieve its existing attempt) to support that case. The API also has no cancellation endpoint, so an unconfirmed attempt that remains `pending` must be resumed or reconciled with the workshop before another attempt is started.
