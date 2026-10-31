# TallerClaro

TallerClaro is a PayPal AI Hackathon project for carpentry quotes, customer payment journeys, and workshop order tracking. The current repository contains a responsive React frontend demonstration. The backend, AI quote service, database, authentication, and PayPal integration are not implemented yet.

## Current project status

The frontend follows the connected Penpot design and includes workshop and customer screens. Example orders, estimates, payment states, and receipt records are illustrative. Demo actions are stored in the browser and do not contact PayPal, charge a customer, upload a receipt, or call an AI service.

## Run the current project locally

### 1. Install prerequisites

- Install a current Node.js LTS release with npm.
- Clone this repository and open a terminal in the repository folder.

### 2. Install frontend dependencies

```bash
cd frontend
npm ci
```

### 3. Start the development server

```bash
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173/`. Keep the terminal running while you use the app. Vite refreshes the page when frontend source files change.

### 4. Explore the screens

Use the left navigation on desktop or the menu button on a phone. The customer request flow is available from **New order** or **Ask TallerClaro**. You can also open the screens directly using these hash routes:

| Route | Screen |
| --- | --- |
| `#/dashboard` | Workshop summary and recent orders |
| `#/orders` | Searchable and filterable order list |
| `#/quotes` | Quote overview and estimates awaiting approval |
| `#/receipts` | Local receipt records and spending summary |
| `#/accounting` | Illustrative monthly income and expenses |
| `#/customer/new` | Customer project request |
| `#/customer/quote` | Example quote and deposit review |
| `#/customer/tracking` | Order progress and payment summary |
| `#/order/TC-1048` | Workshop order details and status editor |

### 5. Run checks or preview a production build

```bash
npm run lint
npm run build
npm run preview
```

`npm run preview` serves the generated `frontend/dist` build locally. Stop either local server with `Ctrl+C` in its terminal.

## Demo data and limitations

- The mock service stores workshop examples and interactions in the browser's `localStorage` key `tallerclaro.demo.v1`.
- Clear that key in browser developer tools to restore the initial sample data.
- Quote creation uses a fixed illustrative estimate; it does not calculate a real workshop price or call an AI model.
- Approval and PayPal buttons update local demo state only. No payment request is sent and no charge is made.
- Receipt selection records the file name only; the file is not uploaded or retained.
- The demo has no authentication or server-side persistence. Do not enter real customer or payment data.

## Implemented frontend screens

- Workshop dashboard with summary metrics and recent orders.
- Searchable orders, order details, progress, and local status updates.
- Quote list, customer request form, estimate review, and demo approval.
- Receipt records and an illustrative spending summary.
- Illustrative accounting view.
- Customer order tracking, receipt summary, and deposit/balance examples.
- Responsive layouts for laptop, tablet, and phone portrait/landscape viewports.

## Repository layout

- `frontend/` - React 19 and Vite application.
- `frontend/docs/API_CONTRACT.md` - proposed API boundary, data models, and backend requirements.
- `frontend/docs/DESIGN_REFERENCE.md` - Penpot screens and visual values inspected for implementation.
- `REQUIREMENTS.md` - product scope and functional/non-functional requirements.
- `PRODUCT.md` - confirmed product facts and demo constraints.
