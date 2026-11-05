# TallerClaro backend

Monolito FastAPI organizado por capas para cotizaciones, pedidos y pagos de TallerClaro.

## Estado actual

- Arquitectura por capas: `domain`, `application`, `infrastructure`, `presentation`, `bootstrap`.
- Entidades de dominio con `Decimal`, estados validados y reglas de negocio.
- Casos de uso para cotizaciones, pedidos y pagos.
- Repositorios PostgreSQL, servicios de IA y procesador de PayPal desacoplados mediante interfaces de aplicación; el procesador PayPal delega transporte HTTP y parseo de respuestas en colaboradores independientes.
- Reserva de captura separada del contrato general de pedidos mediante un protocolo dedicado expuesto por el Unit of Work.
- Cálculo de importes y elegibilidad de pagos centralizados en el dominio; los casos de uso solo cargan datos, autorizan, coordinan y persisten.
- Endpoints HTTP documentados en OpenAPI bajo `/api`.
- Pruebas unitarias, de aplicación y de API con dobles de memoria.

**Pendiente de conexión real:**

- PostgreSQL en Supabase: configurar `DATABASE_URL` y verificar conexión y esquema.
- IA: configurar `TALLERCLARO_AI_PROVIDER`, `TALLERCLARO_AI_API_KEY` y `TALLERCLARO_AI_MODEL`.
- PayPal Sandbox: configurar `TALLERCLARO_PAYPAL_MODE=sandbox`, `TALLERCLARO_PAYPAL_CLIENT_ID`, `TALLERCLARO_PAYPAL_CLIENT_SECRET` y las URL HTTPS de retorno/cancelación.
- Verificar concurrencia con PostgreSQL y recuperación operativa de capturas inciertas; los dobles de memoria no prueban estas integraciones.

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

Configura `TALLERCLARO_WORKSHOP_PASSWORD_HASH` con un hash bcrypt válido; el
servidor rechaza un hash ausente o inválido al arrancar. Para generarlo sin
introducir la contraseña en el historial de comandos, desde `Backend/` ejecuta:

```bash
.venv/bin/python -c 'import bcrypt, getpass; print(bcrypt.hashpw(getpass.getpass().encode(), bcrypt.gensalt()).decode())'
```

Si PostgreSQL no está disponible al arrancar, el proceso falla y debe reiniciarse.

Arranca el servidor local con FastAPI CLI (`fastapi[standard]`):

```bash
fastapi dev src/tallerclaro/main.py
```

Documentación interactiva: <http://127.0.0.1:8000/docs>

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
al abrir cada transacción. La conexión recomendada es el Session Pooler
(`5432`); la compatibilidad real del entorno desplegado requiere verificación.

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

## Pruebas

```bash
python -m pytest
# o
uv run pytest
```

Las pruebas usan dobles en memoria y no requieren PostgreSQL ni PayPal.
Su configuración se aísla del `.env` local y de las variables de credenciales
del proceso para evitar conexiones accidentales a servicios reales.

Verificación local del 2026-11-04: `python -m pytest -q` produjo 269 pruebas
aprobadas y una advertencia de deprecación de `pytest-asyncio` con Python 3.14.
TestClient se bloqueó dentro del sandbox del agente y la suite se ejecutó fuera
de él; no se demostró que los plugins fueran la causa. No se validaron servicios
reales ni capturas simultáneas contra PostgreSQL.

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
        paypal_transport.py
        paypal_parsing.py
      security/
        token_service.py
        workshop_auth.py
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

- Sin autenticación: `GET /api/health` y `POST /api/quotes`; esta última devuelve el token del cliente.
- Taller: `GET /api/orders`, `PATCH /api/orders/{id}` y `POST /api/quotes/{id}/generate` requieren Basic Auth; el servidor verifica la contraseña contra `TALLERCLARO_WORKSHOP_PASSWORD_HASH`.
- Cliente: crear, consultar y capturar pagos requieren `X-Customer-Token` o `Authorization: Bearer`.
- Lectura, aprobación y rechazo de cotizaciones, y detalle de pedido, aceptan token del cliente o Basic del taller mediante `PrincipalDep`, con validación de pertenencia en aplicación.

## Configuración

La configuración se define en `bootstrap/settings.py` y la plantilla es `.env.example`.
Se usa el prefijo `TALLERCLARO_`, con `DATABASE_URL` como alias recomendado para PostgreSQL.
El hash del taller no tiene un valor predeterminado utilizable. Cambia también el
secreto de tokens de ejemplo y configura `TALLERCLARO_CORS_ORIGINS` para el frontend.

No incluir secretos en el código ni en variables `VITE_*`.

## PostgreSQL

El esquema fuente de verdad está en [`database/schema.sql`](../database/schema.sql).
Incluye 001–002 y la columna de reserva de 003 al crear tablas nuevas. En bases
existentes, `CREATE TABLE IF NOT EXISTS` no añade esa columna: aplica la migración
003 por separado antes del despliegue, con autorización explícita. No hay runner
automático; consulta [`database/README.md`](../database/README.md).

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

Define `TALLERCLARO_PAYPAL_RETURN_URL` y `TALLERCLARO_PAYPAL_CANCEL_URL` como
URL HTTPS del frontend, por ejemplo `https://example.org/#/customer/payment/return`
y `https://example.org/#/customer/payment/cancel`. Se validan al construir el
procesador; con PayPal habilitado, una URL ausente o inválida impide el arranque.

Antes de capturar se persiste `pedido.captura_en_curso`. Otros pagos del pedido
quedan bloqueados hasta completar y guardar el intento reservado. El POST de
captura lleva una clave `PayPal-Request-Id` estable por orden PayPal. Tras una
respuesta HTTP no exitosa se consulta la orden y se valida una captura completada.
Un fallo de conexión, timeout o protocolo HTTP se normaliza a
`PAYMENT_PROVIDER_ERROR` (HTTP 502), sin exponer secretos ni excepciones HTTPX.
No dispara una consulta adicional: requiere reintentar el mismo pago;
no hay conciliación en segundo plano, liberación automática por vencimiento ni
herramienta de resolución manual. Los errores mantienen la reserva. La
recuperación local se probó con dobles, y la idempotencia del proveedor y la
concurrencia real siguen pendientes de validación en Sandbox/PostgreSQL.

## Arquitectura

- `domain`: Python puro, entidades y reglas. No depende de FastAPI, Pydantic, ORM ni SDK.
- `application`: casos de uso e interfaces `Protocol` documentadas. Depende solo del dominio y de sus DTOs.
- `infrastructure`: repositorios PostgreSQL, integraciones de IA y pagos que implementan las interfaces. El procesador PayPal es una fachada sobre `paypal_transport.py` (HTTP/OAuth) y `paypal_parsing.py` (validación pura de respuestas). `infrastructure/security/workshop_auth.py` concentra bcrypt y la validación del hash usada en arranque y autenticación.
- `presentation/http`: routers, esquemas Pydantic, extracción de credenciales HTTP y autorización. Delega a los casos de uso; no calcula dinero.
- `bootstrap` y `main.py`: configuración, composición mediante factorías registrables y arranque.
- Los protocolos de repositorios, servicios, pagos y reserva de captura describen precondiciones, resultados, errores y semántica transaccional; los dobles de `tests/fakes.py` respetan las mismas firmas y la misma semántica de commit/rollback.

## Matriz de aceptación local S.O.L.I.D.

Esta matriz documenta los criterios de la especificación SDD del refactor. Las
firmas son comprobaciones auxiliares; el comportamiento se verifica con los
escenarios enlazados. Las pruebas SQL usan cursores controlados, no un servidor:
no certifican constraints, ejecución SQL ni concurrencia real de PostgreSQL.

| ID | Implementación | Evidencia local |
| --- | --- | --- |
| S1 | `Order` centraliza pagado, saldo, importe solicitado y elegibilidad; aplicación coordina | [Reglas monetarias](tests/domain/test_payment_rules.py), [captura](tests/application/test_capture_contract.py) |
| S2 | PayPal separa fachada, transporte y parsers puros | [Parsing](tests/unit/test_paypal_parsing.py), [fallos de transporte](tests/unit/test_paypal_transport_errors.py) |
| S3 | `workshop_auth.py` concentra bcrypt para arranque y autenticación | [Autenticación](tests/unit/test_workshop_auth_hash.py), [arranque](tests/unit/test_database_startup.py) |
| O1 | Registros de factorías de IA y pagos con dependencias inyectadas | [Extensión de factorías](tests/unit/test_factory_registration.py) |
| L1 | Errores de transporte normalizados; repositorios del UoW se resuelven solo en contexto; tokens con reloj y vencimiento | [UoW](tests/unit/test_unit_of_work_contract.py), [tokens](tests/unit/test_customer_token_contract.py), [repositorios](tests/unit/test_repository_contracts.py), [HTTP 502](tests/api/test_payments.py) |
| I1 | `CaptureReservationRepository` separado de pedidos; contratos sin lookup de pago no consumido | [Reservas](tests/unit/test_capture_reservation_contract.py), [firmas auxiliares](tests/unit/test_protocol_conformance.py) |
| D1 | Dominio y aplicación independientes de frameworks, configuración e infraestructura | [Dependencias de capas](tests/unit/test_architecture_dependencies.py) |

Resolver repositorios mediante un UoW, así como hacer commit o rollback, exige
contexto activo en PostgreSQL y en el fake. Esto no invalida automáticamente
referencias de repositorios obtenidas previamente. La preparación de fixtures
del fake usa contextos explícitos y commit; la lectura usa contextos propios.

Los tokens se rechazan si son desconocidos, alterados, usados o si su vencimiento
es anterior al instante UTC actual. El instante exacto de vencimiento conserva
el comportamiento existente (`expiration < now`). Ambos servicios aceptan un
reloj opcional por nombre; el rollback del fake restaura datos sin copiar el reloj.

La compatibilidad de rutas y campos de pagos se comprueba en
[contrato HTTP](tests/api/test_http_contract.py); las pruebas de autenticación
conservan la separación taller/cliente. No se cambian las limitaciones del
frontend ni se añade resolución operativa de capturas.
