# TallerClaro

TallerClaro is a PayPal AI Hackathon project for carpentry quotes, customer payment journeys, and workshop order tracking. The repository contains a React 19 + Vite frontend and a Python/FastAPI backend organized as a layered monolith (`presentation`, `application`, `domain`, `infrastructure`, `bootstrap`).

## Current project status

- **Frontend (`frontend/`)**: Implements workshop and customer screens following the Penpot design system, with explicit separation between local **Demo mode** (`localStorage`) and **Real API mode** connected to the FastAPI backend (`src/services/apiClient.js`).
- **Backend (`Backend/`)**: Implements domain entities, business rules (`Decimal` USD calculations, 50% deposit, status transitions, payment verification before delivery), use cases, PostgreSQL repositories, OpenAI-compatible AI quote & clarification adapter, PayPal Sandbox adapter, workshop Basic Auth, and signed `X-Customer-Token` link authorization.
- **Database (`database/`)**: PostgreSQL schema (`database/schema.sql`) and migrations (`database/migrations/001_add_customer_link_tokens.sql`, `002_add_quote_clarification_fields.sql`) ready for deployment on **Supabase** (in the isolated `tallerclaro` schema).
- **Pending live credentials**: Connecting the Supabase PostgreSQL instance (`DATABASE_URL`), configuring a live `TALLERCLARO_AI_API_KEY`, and running end-to-end Sandbox captures with live PayPal Sandbox credentials.

## Run the frontend locally

### 1. Install prerequisites

- Install a current Node.js LTS release and **`pnpm`**.
- Clone this repository and open a terminal in the repository folder.

### 2. Install frontend dependencies

```bash
cd frontend
pnpm install
```

### 3. Start the development server

```bash
pnpm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173/`. By default, the frontend runs in local Demo mode unless `VITE_APP_MODE=real` (or `VITE_API_BASE_URL`) is configured to point at the running FastAPI backend.

### 4. Explore the screens

Use the left navigation on desktop or the menu button on a phone. The customer request flow is available from **New order** or **Ask TallerClaro**. You can also open the screens directly using these hash routes:

| Route | Screen |
| --- | --- |
| `#/dashboard` | Workshop summary and recent orders |
| `#/orders` | Searchable and filterable order list |
| `#/quotes` | Quote overview and estimates awaiting approval |
| `#/receipts` | Local receipt records and spending summary |
| `#/accounting` | Illustrative monthly income and expenses |
| `#/customer/new` | Customer project request and AI clarification flow |
| `#/customer/quote` | Quote breakdown and deposit review |
| `#/customer/tracking` | Order progress, payment summary, and PayPal checkout |
| `#/order/TC-1048` | Workshop order details and status editor |

### 5. Run checks or preview a production build

```bash
pnpm run lint
pnpm run build
pnpm run preview
```

## Run the backend locally

With Python 3.11+ (or Python 3.14 in `Backend/.venv`), from the repository root:

```bash
cd Backend
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
fastapi dev src/tallerclaro/main.py
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.
The API runs at `http://127.0.0.1:8000`; `/docs` provides the generated OpenAPI UI.

### Main API endpoints (`/api`)

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Application liveness check |
| `POST` | `/api/quotes` | Create customer and draft quote (returns `customer_token`) |
| `GET` | `/api/quotes/{id}` | Retrieve quote details (Workshop Basic Auth or `X-Customer-Token`) |
| `POST` | `/api/quotes/{id}/generate` | Generate AI quote breakdown or clarification questions |
| `POST` | `/api/quotes/{id}/approve` | Approve quote and create workshop order with 50% deposit |
| `POST` | `/api/quotes/{id}/reject` | Reject pending quote |
| `GET` | `/api/orders` | List and filter workshop orders (Workshop Basic Auth) |
| `GET` | `/api/orders/{id}` | Retrieve order details, payments, and remaining balance |
| `PATCH` | `/api/orders/{id}` | Update order status or estimated delivery date (Workshop Basic Auth) |
| `POST` | `/api/orders/{id}/payments` | Create PayPal Sandbox order for deposit or balance (`X-Customer-Token`) |
| `POST` | `/api/payments/{id}/capture` | Capture PayPal payment and update order accounting (`X-Customer-Token`) |
| `GET` | `/api/payments/{id}` | Retrieve payment attempt status (`X-Customer-Token`) |

Run the backend test suite (in-memory fakes, no external DB/network required):

```bash
cd Backend
.venv/bin/pytest
```

See [backend setup and architecture](Backend/README.md) for environment variables and layer responsibilities.

## Demo mode vs Real mode

- **Demo mode (`localStorage`)**: Stores sample workshop data under `tallerclaro.demo.v1`. Clearly labeled in the UI as simulated demonstration data; does not contact PayPal or charge real money.
- **Real mode (FastAPI + Supabase PostgreSQL + AI + PayPal Sandbox)**: Connects to `/api` endpoints, enforces workshop Basic Auth and customer link tokens (`X-Customer-Token`), and requires server-side credentials in `Backend/.env`.

## Repository layout

- `frontend/` - React 19 and Vite application managed with `pnpm`.
- `Backend/` - Python/FastAPI layered monolith (`presentation`, `application`, `domain`, `infrastructure`, `bootstrap`) and `pytest` suite.
- `database/` - PostgreSQL schema (`schema.sql`) and migrations (`migrations/`). See the [database guide](database/README.md).
- `AGENTS.md` - Development guidelines, package manager rules, and infrastructure constraints.
- `REQUIREMENTS.md` - Product scope and functional/non-functional requirements.
- `PRODUCT.md` - Confirmed product facts and constraints.
- `frontend/docs/API_CONTRACT.md` - API boundary, data models, and backend contract.
- `frontend/docs/DESIGN_REFERENCE.md` - Penpot screens and visual design reference.
