# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Small carpentry workshop owners who need to prepare estimates, organize active jobs, review material receipts, and understand customer payments. Their customers describe a custom piece, review an estimate, and follow the order.

## Product Purpose

TallerClaro supports a carpentry order from the customer's first project request through quote review, deposit, production, receipts, and final balance. Success means a customer and workshop can understand the agreed work, price, and current next step.

## Positioning

The product connects customer-friendly project requests with workshop order tracking and transparent material spending. AI-assisted estimate generation and PayPal payments are intended to be provided by backend services; the current frontend uses clearly labeled demo behavior.

## Operating Context

The product is a web application for a carpentry business. A workshop may review a quote, update an order stage, attach material receipts, and track example income and expenses. A customer may describe a project, review an estimate, and view order progress.

## Capabilities and Constraints

- The repository contains a React 19 and Vite web frontend.
- The required order stages are `pending`, `paid`, `in_progress`, and `delivered`; the designs also show quote sent and ready to finish states.
- PayPal Sandbox payments, AI quote generation, pricing validation, authenticated workshop actions, and persisted backend data are not implemented in the frontend.
- Demo data may be stored in browser local storage. It must not be described as backend-verified or as a real payment.
- Payable amounts and payment results must be validated by the backend.
- No production payment processing, inventory management, employee scheduling, customer accounts, invoicing, or accounting/ERP integration is in scope.

## Brand Commitments

The product name is TallerClaro. The inspected Penpot file is the primary visual reference. The sample workshop is named Madera Norte; its sample customer names and figures are illustrative.

## Evidence on Hand

- `REQUIREMENTS.md` defines product scope, business rules, and technical constraints.
- The connected Penpot file contains four workshop screens and three customer journey screens.
- No backend API specification or production credentials are present in the repository.

## Product Principles

- Keep the customer informed about the work and the next step.
- Make estimates and spending understandable.
- Separate quote approval, payment verification, and production status.
- Label illustrative values and simulated actions clearly.
- Keep frontend service boundaries replaceable by backend integrations.
