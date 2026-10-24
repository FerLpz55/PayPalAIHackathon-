# CARPENTRY QUOTE & ORDER MANAGEMENT SYSTEM
## 1. Project Overview
### Purpose
Build a web application that automates quote generation, customer payments, and order management for a carpentry business.

The application will use an AI-powered agent to transform customer requests into structured quotes, integrate PayPal Sandbox for payment processing, and provide a dashboard for tracking order progress.

### Goals
- Simplify the process of requesting and generating carpentry quotes.
- Provide customers with a clear breakdown of materials, labor, and estimated costs.
- Enable customers to review quotes and complete test payments.
- Allow the business to track and update order statuses from a centralized dashboard.

## 2. Scope
### In Scope
- Landing page with a quote generation interface.
- AI-assisted quote generation.
- Structured quote breakdown and price calculation.
- Checkout and payment confirmation page.
- PayPal Sandbox integration.
- Order persistence.
- Order management dashboard.
- Order status updates.
### Out of Scope
- Production payment processing.
- Inventory management.
- Employee scheduling.
- Customer accounts and registration.
- Automated invoicing and tax reporting.
- Integration with real accounting or ERP systems.
## 3. Functional Requirements
### FR-01: Landing Page and Quote Generation
The system shall provide a landing page where customers can describe their carpentry requirements using a chat interface or a structured form.

The system shall send the customer request to an AI-powered agent that generates a structured quote.

The quote shall include:
- Description of the requested work.
- Materials and quantities.
- Material costs.
- Estimated labor costs.
- Additional costs, when applicable.
- Total estimated price.
#### Acceptance Criteria
- Given a valid customer request, when the customer submits it, then the system generates and displays a structured quote.
- Given a request with insufficient information, when the AI agent processes it, then the system requests the missing information or indicates the assumptions used.
- Given an AI service error, then the system displays an understandable error and allows the customer to retry.
### FR-02: Quote Review
The system shall display the generated quote before the customer proceeds to checkout.

The customer shall be able to review the cost breakdown and the final estimated price.

The system shall associate with each quote with a unique identifier.
#### Acceptance Criteria
- The quote displays its line items, quantities, costs, and total.
- The customer can proceed to checkout using the selected quote.
- The checkout amount matches the validated quote total.
- The system prevents unauthorized client-side modifications from changing the payable amount.
### FR-03: Checkout and Payment
The system shall provide a dashboard listing the carpentry orders stored in the application.

Each order shall display, at minimum:
- Order identifier.
- Customer request or project description.
- Total amount.
- Current status.
- Creation date.
The dashboard shall allow authorized users to update an order's status.

Supported statuses:
- pending
- paid
- in_progress
- delivered
#### Acceptance Criteria
- The dashboard displays existing orders.
- Each order displays its current status.
- A user can change an order's status using a simple interface.
- Status changes are persisted and remain visible after reloading the dashboard.
- Updating one order does not modify another order.
### FR-05: Order Persistence
The system shall persist quotes, orders, and relevant payment information.

Each order shall reference its corresponding quote.

The checkout page and dashboard shall use the same persisted order data.
#### Acceptance Criteria
- Each created order receives a unique identifier.
- Order data remains available after a page reload.
- The quote total and order total remain consistent.
- Payment status is based on verified payment information.
## 4. Business Rules
- BR-01: Every quote must contain a project description, a cost breakdown, and a total estimated price.
- BR-02: Customers must review their quote before proceeding to checkout.
- BR-03: AI-generated estimates must be validated against application-defined pricing rules before becoming payable quotes.
- BR-04: The backend is responsible for calculating or validating the final payable amount.
- BR-05: An order must not be marked as paid solely because the customer reaches a success page.
- BR-06: Order status changes must be persisted.
- BR-07: The initial order status shall be pending.
- BR-08: Payment confirmation and order fulfillment status must be handled separately. A delivered order must have a verified payment unless an explicitly defined business exception applies.
## 5. Non-Functional Requirements
### NFR-01: Usability
The application shall provide a simple and intuitive interface suitable for non-technical users.

### NFR-02: Responsiveness
The landing page, checkout page, and dashboard shall be usable on desktop and mobile devices.

### NFR-03: Security
- API keys and sensitive credentials must not be exposed in client-side code.
- The backend must validate payment amounts and payment results.
- Access to order management operations must be restricted to authorized users or an explicitly defined demo mode.
### NFR-04: Reliability
The system shall handle AI service failures, invalid inputs, and payment errors without crashing.

### NFR-05: Data Integrity
Quotes, orders, totals, and payment statuses shall remain consistent across application views.

### NFR-06: Maintainability
The application shall separate quote generation, payment processing, and order management into clearly defined modules.

## 6. Technical Constraints
- Payment provider: PayPal Sandbox.
- AI integration: An AI service accessed through the backend.
- Order statuses: pending, paid, in_progress, and delivered.
- Data storage: Persistent database or equivalent storage.
- Deployment: A working demo must be accessible for evaluation.
- Environment configuration: Credentials and API keys must be provided through environment variables.
## 7. Views and Navigation
### View 1: Landing Page and Quote Generator
Responsibilities:

- Present the carpentry business and its services.
- Collect customer requirements.
- Interact with the AI agent.
- Display the generated quote.
- Provide an action to proceed to checkout.
### View 2: Checkout and Confirmation
Responsibilities:

- Display the selected quote and total.
- Initiate PayPal Sandbox payment.
- Display payment success, failure, or cancellation.
- Show the verified order status.
### View 3: Order Management Dashboard
Responsibilities:

- List existing orders.
- Display order details and statuses.
- Allow authorized status updates.
- Reflect persisted changes.
## 8. Definition of Done
The MVP is considered complete when:

- A customer can submit a carpentry request.
- The AI agent generates a structured quote.
- The customer can review the quote before checkout.
- The customer can initiate and complete a PayPal Sandbox payment.
- Payment results are validated by the backend.
- Orders and quotes are persisted.
- The dashboard lists existing orders.
- Order statuses can be updated and persisted.
- The application handles basic input, AI, and payment errors.
- The complete flow can be demonstrated from quote generation to order management.