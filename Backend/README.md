# TallerClaro backend

Monolito FastAPI organizado por capas para cotizaciones, pedidos y pagos de TallerClaro.

## Estado actual

- Arquitectura por capas: `domain`, `application`, `infrastructure`, `presentation`, `bootstrap`.
- Entidades de dominio con `Decimal`, estados validados y reglas de negocio.
- Casos de uso para cotizaciones, pedidos y pagos.
- Repositorios PostgreSQL, adaptadores de IA y PayPal detrás de puertos.
- Endpoints HTTP documentados en OpenAPI bajo `/api`.
- Pruebas unitarias, de aplicación y de API con dobles de memoria.

**Pendiente de conexión real:**
- PostgreSQL desplegado: configurar `TALLERCLARO_DATABASE_*` y aplicar migraciones.
- IA: configurar `TALLERCLARO_AI_PROVIDER`, `AI_API_KEY` y `AI_MODEL`.
- PayPal Sandbox: configurar `TALLERCLARO_PAYPAL_MODE=sandbox`, `CLIENT_ID` y `CLIENT_SECRET`.

## Desarrollo

Desde `Backend/`, con Python 3.11 o superior y `uv`:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'
```

Copia la plantilla de configuración:

```bash
cp .env.example .env
# Edita .env con los valores reales.
```

Arranca el servidor local con FastAPI CLI (`fastapi[standard]`):

```bash
fastapi dev src/tallerclaro/main.py
```

Documentación interactiva: http://127.0.0.1:8000/docs

En Windows PowerShell, activar con `.venv\Scripts\Activate.ps1`.

## Pruebas

```bash
python -m pytest
# o
uv run pytest
```

Las pruebas usan dobles en memoria y no requieren PostgreSQL ni PayPal.

## Estructura

```text
Backend/
  pyproject.toml
  .env.example
  src/tallerclaro/
    main.py
    bootstrap/
      settings.py
    domain/
      entities.py
      value_objects.py
      exceptions.py
    application/
      ports.py
      dtos.py
      exceptions.py
      use_cases/
        quotes.py
        orders.py
        payments.py
    infrastructure/
      db/
        connection.py
        unit_of_work.py
        repositories.py
      ai/
        adapter.py
      payment/
        paypal_adapter.py
      security/
        token_service.py
    presentation/http/
      routers/
        health.py
        quotes.py
        orders.py
        payments.py
      schemas/
        health.py
        quotes.py
        orders.py
        payments.py
        common.py
      dependencies.py
      exception_handlers.py
  tests/
    domain/
    application/
    api/
    fakes.py
```

## API

Prefijo: `/api`

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/health` | Comprobación de vida |
| POST | `/quotes` | Crear cliente y cotización draft |
| GET | `/quotes/{id}` | Consultar cotización |
| POST | `/quotes/{id}/generate` | Generar propuesta con IA |
| POST | `/quotes/{id}/approve` | Aprobar cotización y crear pedido |
| POST | `/quotes/{id}/reject` | Rechazar cotización |
| GET | `/orders` | Listar pedidos del taller |
| GET | `/orders/{id}` | Consultar pedido con pagos y saldo |
| PATCH | `/orders/{id}` | Actualizar estado/fecha estimada |
| POST | `/orders/{id}/payments` | Crear intento de pago PayPal |
| POST | `/payments/{id}/capture` | Capturar pago en PayPal |
| GET | `/payments/{id}` | Consultar intento de pago |

### Autorización

- Operaciones del taller (`/orders`, `PATCH /orders`) requieren Basic Auth con las credenciales de demo configuradas en el servidor.
- Operaciones del cliente (`/orders/{id}/payments`, `/payments/{id}/capture`, `/payments/{id}`) requieren un token de enlace en el header `X-Customer-Token`.

## Configuración

Toda la configuración sensible se lee desde variables de entorno con prefijo `TALLERCLARO_`. Ver `.env.example`.

No incluir secretos en el código ni en variables `VITE_*`.

## PostgreSQL

El esquema fuente de verdad está en `database/schema.sql`. Los cambios posteriores son migraciones numeradas en `database/migrations/`.

Antes de aplicar una migración en el servidor desplegado, verifica de forma de solo lectura:

```bash
psql -h <host> -U <user> -d <db> -c "SELECT version();"
psql -h <host> -U <user> -d <db> -c "\dt tallerclaro.*"
psql -h <host> -U <user> -d <db> -c "\d tallerclaro.cotizacion"
```

No ejecutes migraciones ni pruebas que escriban contra el servidor desplegado sin confirmar el entorno.

## Reglas de negocio clave

- Moneda única: USD.
- Cálculo de importes con `Decimal` y redondeo a dos decimales.
- La IA propone partidas; el servidor valida y calcula el total.
- Una cotización debe estar en `pending_review` para aprobarse o rechazarse.
- Al aprobarse, se crea como máximo un pedido con anticipo del 50 %.
- Los pagos se confirman solo tras verificar la respuesta de PayPal en el servidor.
- No se entrega un pedido sin el pago total verificado.

## Integraciones

### IA

Configura un proveedor compatible con OpenAI. Si no hay credenciales, el adaptador devuelve un error `SERVICE_UNAVAILABLE` claro.

### PayPal

Configura modo `sandbox` con credenciales reales de Sandbox. Si no hay credenciales, el adaptador devuelve `SERVICE_UNAVAILABLE`. No se simulan pagos exitosos en la API real.

## Arquitectura

- `domain`: Python puro, entidades y reglas. No depende de FastAPI, Pydantic, ORM ni SDK.
- `application`: casos de uso y puertos `Protocol`. Depende del dominio.
- `infrastructure`: repositorios PostgreSQL y adaptadores que implementan los puertos.
- `presentation/http`: routers, esquemas Pydantic y autorización. Delega a los casos de uso.
- `bootstrap` y `main.py`: configuración, composición y arranque.
