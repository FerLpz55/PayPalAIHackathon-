# TallerClaro

TallerClaro is a PayPal AI Hackathon project for carpentry quotes, customer payment journeys, and workshop order tracking. The repository contains a React/Vite frontend demonstration and a Python/FastAPI backend foundation organized as a layered monolith. The backend currently exposes only a health endpoint; database persistence, business use cases, authentication, AI, and PayPal integration remain pending.

## Current project status

The frontend follows the connected Penpot design and includes workshop and customer screens. Example orders, estimates, payment states, and receipt records are illustrative. Demo actions are stored in the browser and do not contact PayPal, charge a customer, upload a receipt, or call an AI service.

The frontend still uses its local mock service and is not connected to the backend. The backend architecture and current scope are defined in the [backend plan](docs/superpowers/plans/2026-10-31-fastapi-layers.md); [backend setup](Backend/README.md) documents the runnable implementation.

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

## Run the backend locally

With Python 3.11 or newer, from the repository root:

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn tallerclaro.main:app --app-dir src --reload
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.
The API runs at `http://127.0.0.1:8000`; `/docs` provides the generated OpenAPI UI.
`GET /api/health` returns `200` with `{"status":"ok"}`. This checks application
liveness, not database or provider connectivity. Run `python -m pytest` from
`Backend/` to execute the backend tests.

See [backend setup and architecture](Backend/README.md) for configuration and layer responsibilities.

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
- `Backend/` - Python/FastAPI layered monolith foundation and API test.
- `database/` - PostgreSQL schema scripts and related files; schema and backend connection are pending. See the [database guide](database/README.md).
- `docs/superpowers/plans/2026-10-31-fastapi-layers.md` - backend architecture, implemented foundation, and pending work.
- `frontend/docs/API_CONTRACT.md` - proposed API boundary, data models, and backend requirements.
- `frontend/docs/DESIGN_REFERENCE.md` - Penpot screens and visual values inspected for implementation.
- `REQUIREMENTS.md` - product scope and functional/non-functional requirements.
- `PRODUCT.md` - confirmed product facts and demo constraints.
