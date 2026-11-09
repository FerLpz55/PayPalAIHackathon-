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

On an approval return, the frontend reads the saved internal `payment_id`, calls `GET /api/payments/{payment_id}`, checks that the returned order and PayPal order IDs match the saved attempt, and calls `POST /api/payments/{payment_id}/sync` to reconcile it. The backend only captures while PayPal reports the order as `APPROVED`, and the frontend displays success only if the matching backend record reports `completed`. On the cancellation route, the frontend reads backend state and may call `POST /api/payments/{payment_id}/cancel` for the saved attempt; cancellation never releases an uncertain reservation.

Both payment reads and `sync`/`cancel` use `CustomerTokenDep`; the handlers derive the authorized quote ID and the payment use cases check that it belongs to the order. This is source-level authorization evidence, not a live authorization test. If browser storage is lost before return, a workshop-reissued customer link (or `GET /api/customer/context`) lets the customer recover the order context, but the frontend still does not reconstruct a payment association from the PayPal URL token alone. Pending attempts are also reconciled by the PayPal webhook and the background worker.
