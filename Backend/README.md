# TallerClaro backend

Monolito FastAPI organizado por capas para cotizaciones, pedidos y pagos de TallerClaro.

## Estado actual

- Arquitectura por capas: `domain`, `application`, `infrastructure`, `presentation`, `bootstrap`.
- Entidades de dominio con `Decimal`, estados validados y reglas de negocio.
- Casos de uso para cotizaciones, pedidos y pagos.
- Repositorios PostgreSQL, servicios de IA y procesador de PayPal desacoplados mediante interfaces de aplicación (S.O.L.I.D.).
- Endpoints HTTP documentados en OpenAPI bajo `/api`.
- Pruebas unitarias, de aplicación y de API con dobles de memoria.

**Pendiente de conexión real:**
- PostgreSQL en Supabase: configurar `DATABASE_URL` y verificar conexión y esquema.
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

### Conexión a PostgreSQL en Supabase

Al ejecutar desde `Backend/`, el backend carga automáticamente `.env`. Puedes
mantener la URL de tu base de Supabase en `DATABASE_URL` usando el **Session Pooler**
(puerto `5432`, compatible con IPv4 y sesiones persistentes de FastAPI), por
ejemplo con valores ficticios:

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:example%402026@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

El pool de conexiones (`Database`) desactiva prepared statements automáticos
(`prepare_threshold=None`) y `PostgresUnitOfWork` aplica `SET LOCAL TRANSACTION ISOLATION LEVEL SERIALIZABLE`
al abrir cada transacción, por lo que funciona tanto con el Session Pooler
(`5432`), el Transaction Pooler (`6543`) o conexión directa de Supabase.

Se mantiene `TALLERCLARO_DATABASE_URL` por compatibilidad. Dentro de cada fuente
de configuración gana `DATABASE_URL`; las variables del proceso prevalecen sobre
`.env`, y los argumentos explícitos de `Settings` prevalecen sobre ambas.
Si no hay URL, se usan los campos `TALLERCLARO_DATABASE_*` de la plantilla.

La URL tiene prioridad sobre esos campos: usuario, base, puerto y SSL se toman
de la propia URL. El backend normaliza en memoria los `@` sin escapar de la
contraseña y conserva los ya codificados como `%40`, sin modificar `.env`.
Los demás caracteres reservados deben estar codificados en la URL.

`GET /api/health` comprueba la disponibilidad HTTP; no verifica PostgreSQL.
La conexión real se comprueba por separado con consultas de solo lectura y
revisando que existan el esquema y las migraciones necesarias. No aplicar
migraciones automáticamente contra la base desplegada.

En Windows PowerShell, activar con `.venv\Scripts\Activate.ps1`.

## Asistente contable

`GET /api/accounting/summary` y `POST /api/accounting/assistant` (Basic Auth del taller).

- El dominio (`domain/accounting.py`) calcula los totales con `Decimal`: valor de los pedidos,
  dinero cobrado (solo pagos `completed`), anticipos, saldos y monto pendiente.
- La IA solo explica esas cifras en lenguaje simple; no calcula ni inventa importes.
- Al proveedor de IA se envían únicamente totales agregados, nunca nombres, correos ni
  identificadores de clientes (minimización de datos, Ley 29733).
- La llamada a la IA se hace fuera de la transacción SQL. Sin IA configurada responde
  `SERVICE_UNAVAILABLE`; el resumen sigue disponible.
- Los gastos y costos de materiales aún no se registran, por lo que el asistente no
  calcula ganancias y lo indica cuando se le pregunta.

## Pruebas

```bash
python -m pytest
# o
uv run pytest
```

Las pruebas usan dobles en memoria y no requieren PostgreSQL ni PayPal.
Su configuración se aísla del `.env` local y de las variables de credenciales
del proceso para evitar conexiones accidentales a servicios reales.

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
      interfaces.py
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
        service.py
      payment/
        paypal_processor.py
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

El esquema fuente de verdad está en `database/schema.sql`, que incorpora las migraciones 001 y 002. Los cambios posteriores son migraciones numeradas en `database/migrations/`.

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

Configura un proveedor compatible con OpenAI. Si no hay credenciales, el servicio devuelve un error `SERVICE_UNAVAILABLE` claro.

### PayPal

Configura modo `sandbox` con credenciales reales de Sandbox. Si no hay credenciales, el procesador devuelve `SERVICE_UNAVAILABLE`. No se simulan pagos exitosos en la API real.

## Arquitectura

- `domain`: Python puro, entidades y reglas. No depende de FastAPI, Pydantic, ORM ni SDK.
- `application`: casos de uso e interfaces `Protocol`. Depende del dominio.
- `infrastructure`: repositorios PostgreSQL, integraciones de IA y procesador de pagos que implementan las interfaces.
- `presentation/http`: routers, esquemas Pydantic y autorización. Delega a los casos de uso.
- `bootstrap` y `main.py`: configuración, composición y arranque.
