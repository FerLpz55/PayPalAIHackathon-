# Frontend API Contract

El backend de TallerClaro expone los siguientes endpoints bajo `/api`. Reemplaza `mockApi.js` con llamadas HTTP a estos endpoints.

## Base URL

Configura la URL base mediante una variable pública del cliente, por ejemplo `VITE_API_BASE_URL`. No incluyas secretos en variables `VITE_*`.

## Autorización

- **Taller**: Basic Auth con el usuario y contraseña de demo configurados en el servidor.
  - `Authorization: Basic <base64(usuario:contraseña)>`
- **Cliente**: token de enlace de un solo uso.
  - `X-Customer-Token: <token>`

El backend nunca expone tokens ni trazas en las respuestas.

## Endpoints

### Salud

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/api/health` | Devuelve `{"status": "ok"}` |

### Cotizaciones

| Método | Endpoint | Descripción |
| --- | --- | --- |
| POST | `/api/quotes` | Crea cliente y cotización en estado `draft` |
| GET | `/api/quotes/:quoteId` | Devuelve cotización, cliente y partidas |
| POST | `/api/quotes/:quoteId/generate` | Pide propuesta a IA; puede devolver `needs_information` |
| POST | `/api/quotes/:quoteId/approve` | Aprueba cotización y crea el pedido (idempotente) |
| POST | `/api/quotes/:quoteId/reject` | Rechaza cotización en `pending_review` |

#### POST /api/quotes

Request:

```json
{
  "customer": {
    "name": "Carlos Ficticio",
    "email": "carlos@example.com",
    "phone": "5555555555"
  },
  "carpenter_id": 1,
  "request": "Mesa de comedor de madera sólida para 6 personas"
}
```

Response 201:

```json
{
  "id": "1",
  "customer_id": "1",
  "carpenter_id": "1",
  "request": "Mesa de comedor de madera sólida para 6 personas",
  "description": null,
  "items": [],
  "currency": "USD",
  "total": null,
  "deposit_amount": null,
  "balance_amount": null,
  "status": "draft",
  "created_at": "2026-11-01T12:00:00Z"
}
```

#### POST /api/quotes/:quoteId/generate

Response 200:

```json
{
  "id": "1",
  "status": "pending_review",
  "description": "Mesa con patas torneadas y acabado barnizado.",
  "items": [
    {
      "id": "1",
      "type": "material",
      "description": "Madera de encino",
      "unit": "pieza",
      "quantity": 2,
      "unit_amount": 100,
      "amount": 200
    },
    {
      "id": "2",
      "type": "labor",
      "description": "Carpintería y ensamble",
      "unit": "servicio",
      "quantity": 1,
      "unit_amount": 150,
      "amount": 150
    }
  ],
  "total": 350,
  "missing_info": null
}
```

Si falta información:

```json
{
  "id": "1",
  "status": "needs_information",
  "description": null,
  "items": [],
  "total": null,
  "missing_info": ["medidas", "tipo de madera"]
}
```

#### POST /api/quotes/:quoteId/approve

Response 200:

```json
{
  "id": "10",
  "quote_id": "1",
  "code": "TC-a1b2c3...",
  "total": 350,
  "deposit_amount": 175,
  "balance_amount": 175,
  "currency": "USD",
  "status": "pending",
  "estimated_delivery_date": null,
  "created_at": "2026-11-01T12:05:00Z"
}
```

### Pedidos

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/api/orders?limit=20&offset=0` | Lista pedidos del taller |
| GET | `/api/orders/:orderId` | Devuelve pedido, cotización, pagos y saldo |
| PATCH | `/api/orders/:orderId` | Actualiza estado y/o fecha estimada |

#### GET /api/orders

Response 200:

```json
{
  "orders": [
    {
      "id": "10",
      "quote_id": "1",
      "code": "TC-a1b2c3...",
      "total": 350,
      "deposit_amount": 175,
      "balance_amount": 175,
      "currency": "USD",
      "status": "pending",
      "estimated_delivery_date": null,
      "created_at": "2026-11-01T12:05:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### GET /api/orders/:orderId

Response 200:

```json
{
  "id": "10",
  "quote_id": "1",
  "code": "TC-a1b2c3...",
  "total": 350,
  "deposit_amount": 175,
  "balance_amount": 175,
  "currency": "USD",
  "status": "paid",
  "estimated_delivery_date": "2026-11-15",
  "created_at": "2026-11-01T12:05:00Z",
  "payments": [
    {
      "id": "100",
      "type": "deposit",
      "amount": 175,
      "status": "completed",
      "paypal_order_id": "PAYPAL-1"
    }
  ],
  "paid_amount": 175,
  "remaining_balance": 175
}
```

#### PATCH /api/orders/:orderId

Request:

```json
{
  "status": "in_progress",
  "estimated_delivery_date": "2026-11-15"
}
```

Response 200: pedido actualizado.

### Pagos

| Método | Endpoint | Descripción |
| --- | --- | --- |
| POST | `/api/orders/:orderId/payments` | Crea intento de pago en PayPal |
| POST | `/api/payments/:paymentId/capture` | Captura el pago y verifica en servidor |
| GET | `/api/payments/:paymentId` | Consulta intento de pago |

#### POST /api/orders/:orderId/payments

Request:

```json
{
  "type": "deposit"
}
```

Response 200:

```json
{
  "payment_id": "100",
  "paypal_order_id": "PAYPAL-1",
  "amount": 175,
  "currency": "USD",
  "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=PAYPAL-1"
}
```

#### POST /api/payments/:paymentId/capture

Response 200:

```json
{
  "payment_id": "100",
  "status": "completed",
  "paypal_order_id": "PAYPAL-1",
  "paypal_capture_id": "CAPTURE-PAYPAL-1",
  "amount": 175,
  "currency": "USD",
  "paid_at": "2026-11-01T12:10:00Z"
}
```

## Errores

El backend devuelve errores estructurados:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "field_errors": [
    {"field": "body.request", "message": "Field required"}
  ]
}
```

Códigos comunes:

- `201`: creado
- `404`: recurso no encontrado (`NOT_FOUND`)
- `409`: conflicto de estado o duplicado (`CONFLICT`)
- `422`: entrada inválida (`VALIDATION_ERROR`)
- `401`: no autorizado (`UNAUTHORIZED`)
- `503`: servicio externo no configurado (`SERVICE_UNAVAILABLE`)

## Reglas de integridad

- `total`, `deposit_amount` y `balance_amount` son autoritativos solo cuando provienen del servidor.
- El estado de pago se mantiene separado del estado de avance del pedido.
- Una redirección exitosa del cliente no confirma el pago; solo la captura verificada por el servidor lo hace.
- No se permite entregar un pedido sin pago total verificado.

## Modelos

```ts
type QuoteStatus = 'draft' | 'needs_information' | 'pending_review' | 'approved' | 'rejected';

type OrderStatus = 'pending' | 'paid' | 'in_progress' | 'delivered';

type PaymentStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

type QuoteLineItem = {
  id: string;
  type: 'material' | 'labor' | 'other';
  description: string;
  unit: string;
  quantity: number;
  unit_amount: number;
  amount: number;
};

type Quote = {
  id: string;
  customer_id: string;
  carpenter_id: string;
  request: string;
  description: string | null;
  items: QuoteLineItem[];
  currency: string;
  total: number | null;
  deposit_amount: number | null;
  balance_amount: number | null;
  status: QuoteStatus;
  assumptions?: string[];
  missing_info?: string[];
  created_at: string;
  updated_at: string;
};

type Order = {
  id: string;
  quote_id: string;
  code: string;
  total: number;
  deposit_amount: number;
  balance_amount: number;
  currency: string;
  status: OrderStatus;
  estimated_delivery_date: string | null;
  created_at: string;
  updated_at: string;
};

type Payment = {
  id: string;
  order_id: string;
  type: 'deposit' | 'balance';
  amount: number;
  currency: string;
  status: PaymentStatus;
  paypal_order_id: string | null;
  paypal_capture_id: string | null;
  created_at: string;
  paid_at: string | null;
};
```
