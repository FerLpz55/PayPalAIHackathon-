# TallerClaro backend

Monolito FastAPI organizado por capas para cotizaciones, pedidos y pagos de TallerClaro.

## Estado actual

- Arquitectura por capas: `domain`, `application`, `infrastructure`, `presentation`, `bootstrap`.
- Entidades de dominio con `Decimal`, estados validados y reglas de negocio.
- Casos de uso para cotizaciones, pedidos, pagos y asistente contable.
- Repositorios PostgreSQL, servicios de IA (cotizaciones y asistente contable) y procesador de PayPal desacoplados mediante interfaces de aplicación; el procesador PayPal delega transporte HTTP y parseo de respuestas en colaboradores independientes.
- Asistente contable con IA: resume totales verificados en dominio (sin datos personales de clientes) y explica las cifras en lenguaje simple fuera de las transacciones SQL.
- Reserva de captura separada del contrato general de pedidos mediante un protocolo dedicado expuesto por el Unit of Work.
- Cálculo de importes y elegibilidad de pagos centralizados en el dominio; los casos de uso solo cargan datos, autorizan, coordinan y persisten.
- Endpoints HTTP documentados en OpenAPI bajo `/api`.
- Pruebas unitarias, de aplicación y de API con dobles de memoria (467 pruebas aprobadas).

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

`.env` se resuelve como `Backend/.env` desde la ubicación del paquete, no desde el
directorio de trabajo del proceso. Las variables del proceso siguen teniendo
prioridad sobre el archivo. Las pruebas neutralizan el archivo y las variables
`TALLERCLARO_*`/`DATABASE_URL`, de modo que nunca usan credenciales locales.

Al ejecutar desde `Backend/`, el backend carga automáticamente `.env`. Puedes
mantener la URL de tu base de Supabase en `DATABASE_URL` usando el **Session Pooler**
(puerto `5432`, compatible con IPv4 y sesiones persistentes de FastAPI), por
ejemplo con valores ficticios:

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:example%402026@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

El pool de conexiones (`Database`) desactiva prepared statements automáticos
(`prepare_threshold=None`), usa `check_connection` antes de entregar conexiones,
un timeout de adquisición (`TALLERCLARO_DATABASE_POOL_ACQUIRE_TIMEOUT_SECONDS`,
10 s por defecto) y caduca conexiones inactivas a los 300 s
(`TALLERCLARO_DATABASE_POOL_MAX_IDLE_SECONDS`). Al arrancar se ejecuta
`SELECT 1` para verificar la conexión. `PostgresUnitOfWork` aplica
`SET LOCAL TRANSACTION ISOLATION LEVEL SERIALIZABLE`
al abrir cada transacción. La conexión recomendada es el Session Pooler
(`5432`); la compatibilidad real del entorno desplegado requiere verificación.

Una indisponibilidad del pool se traduce a `503 SERVICE_UNAVAILABLE` sin exponer
la cadena de conexión. Las fases SQL que optan por `uow.execute_sql(...)`
reintentan hasta tres veces un conflicto `SERIALIZABLE`; el reintento cubre solo
la transacción, nunca una operación que ya haya llamado a IA o PayPal.

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

Verificación local del 2026-11-09: `Backend/.venv/bin/pytest Backend` produjo 467 pruebas
aprobadas y una advertencia de deprecación de `pytest-asyncio` con Python 3.14.
No se validaron servicios reales ni capturas simultáneas contra PostgreSQL.

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
      accounting.py
      exceptions.py
    application/
      interfaces.py
      dtos.py
      exceptions.py
      use_cases/
        authorization.py
        quotes.py
        orders.py
        payments.py
        accounting.py
    infrastructure/
      db/
        connection.py
        unit_of_work.py
        repositories.py
      ai/
        service.py
        accounting_service.py
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
        accounting.py
      schemas/
        health.py
        quotes.py
        orders.py
        payments.py
        accounting.py
        common.py
      dependencies.py
      exception_handlers.py
      mappers.py
  tests/
    domain/
    application/
    api/
    unit/
    fakes.py
```

## API

Prefijo: `/api`

| Método | Endpoint | Descripción |
| --- | --- | --- |
| GET | `/health` | Comprobación de vida |
| POST | `/auth/login` | Iniciar sesión del taller (cookie + CSRF) |
| GET | `/auth/session` | Consultar la sesión vigente |
| POST | `/auth/logout` | Revocar la sesión y borrar cookies |
| GET | `/customer/context` | Cotización, pedido e intentos del cliente autenticado |
| POST | `/quotes` | Crear cliente y cotización draft |
| GET | `/quotes/{id}` | Consultar cotización |
| POST | `/quotes/{id}/generate` | Generar propuesta con IA |
| POST | `/quotes/{id}/approve` | Aprobar cotización y crear pedido |
| POST | `/quotes/{id}/reject` | Rechazar cotización |
| POST | `/quotes/{id}/customer-access` | Reemitir el enlace del cliente (solo taller) |
| GET | `/orders` | Listar pedidos del taller |
| GET | `/orders/{id}` | Consultar pedido con pagos y saldo |
| PATCH | `/orders/{id}` | Actualizar estado/fecha estimada |
| POST | `/orders/{id}/payments` | Crear intento de pago PayPal |
| POST | `/payments/{id}/capture` | Capturar pago en PayPal |
| POST | `/payments/{id}/sync` | Conciliar con PayPal: captura solo si está `APPROVED` |
| POST | `/payments/{id}/cancel` | Cancelar un intento pendiente sin liberar reservas inciertas |
| GET | `/payments/{id}` | Consultar intento de pago |
| POST | `/payments/webhook/paypal` | Webhook de PayPal verificado por firma |
| GET | `/accounting/summary` | Resumen financiero del taller |
| POST | `/accounting/assistant` | Preguntar al asistente contable |

### Autorización

- Sin autenticación: `GET /api/health`, `POST /api/quotes` (devuelve el token del cliente) y `POST /api/payments/webhook/paypal`, que se autentica con la firma de PayPal.
- Taller: `POST /api/auth/login`, `GET /api/auth/session` y `POST /api/auth/logout`, además de `GET /api/orders`, `PATCH/DELETE /api/orders/{id}`, `POST /api/quotes/{id}/customer-access`, `GET /api/accounting/summary` y `POST /api/accounting/assistant`.
- El login verifica las credenciales contra `TALLERCLARO_WORKSHOP_PASSWORD_HASH` y emite una sesión opaca de 256 bits. Solo se guarda su SHA-256 en `tallerclaro.sesion_taller`; caduca a los 30 minutos de inactividad o 8 horas absolutas, es revocable y rota en cada login. Cambiar el hash bcrypt invalida las sesiones (huella de credenciales).
- Cookies: `__Host-tallerclaro_session` (`HttpOnly`, `Secure`, `SameSite` configurable con `TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=lax|strict|none`, `Path=/`, sin `Domain`) y `__Host-tallerclaro_csrf` (legible por el JS del mismo origen). Usa `none` cuando el frontend (p. ej. Vercel) y la API estén en sitios distintos; exige HTTPS y CORS con credenciales. Las peticiones autenticadas por cookie que cambian estado exigen `X-CSRF-Token` igual al valor de la cookie CSRF y un `Origin` permitido.
- Basic está desactivado por defecto; solo se acepta con `TALLERCLARO_ENABLE_WORKSHOP_BASIC_AUTH=true` como compatibilidad explícita.
- Cliente: crear, consultar, conciliar (`sync`) y cancelar pagos, y `GET /api/customer/context`, requieren `X-Customer-Token` o `Authorization: Bearer`. El frontend no usa `/capture`: reconcilia con `/sync`, que solo captura si PayPal reporta `APPROVED`. La reemisión de acceso solo la puede solicitar el taller autenticado, revoca los tokens anteriores de la cotización y registra el evento; nunca se recupera acceso usando solo el ID.
- Lectura, aprobación, rechazo y generación de cotizaciones, y detalle de pedido, aceptan token del cliente propietario o sesión del taller mediante `PrincipalDep`, con validación de pertenencia antes y después de la llamada de IA. Un token de cliente inválido nunca concede privilegios del taller.

### Límites de abuso

- Los contadores viven en `tallerclaro.limite_consumo` y se incrementan con `INSERT ... ON CONFLICT DO UPDATE` (atómico, sin `DELETE`). El rechazo responde `429 RATE_LIMITED` con `Retry-After`.
- Login: 5 fallos por usuario e IP cada 15 minutos; un login correcto reinicia el contador.
- Creación de cotizaciones: 5 por minuto por IP. Generación: 5 cada 10 minutos por cotización y 100 por hora por taller; si el límite no está disponible no se llama a la IA. Catálogo de precios: 20 por minuto por actor.
- Los cuerpos JSON se limitan a 64 KiB (`TALLERCLARO_MAX_REQUEST_BODY_BYTES`) antes de procesarlos y responden `413 PAYLOAD_TOO_LARGE`.
- `X-Forwarded-For` solo se usa con `TALLERCLARO_TRUST_PROXY_HEADERS=true`; por defecto se emplea la IP de la conexión.

## Configuración

La configuración se define en `bootstrap/settings.py` y la plantilla es `.env.example`.
Se usa el prefijo `TALLERCLARO_`, con `DATABASE_URL` como alias recomendado para PostgreSQL.
El hash del taller no tiene un valor predeterminado utilizable. Cambia también el
secreto de tokens de ejemplo y configura `TALLERCLARO_CORS_ORIGINS` para el frontend.
Si el frontend y la API están en sitios distintos, usa
`TALLERCLARO_WORKSHOP_SESSION_COOKIE_SAMESITE=none` (HTTPS y CORS con credenciales);
en el mismo sitio, el valor por defecto `lax` es suficiente.

`TALLERCLARO_ENVIRONMENT` acepta `development`, `test` y `release`. En `release`
el arranque rechaza secretos de plantilla, CORS con comodines o sin HTTPS,
PayPal incompleto (incluido `TALLERCLARO_PAYPAL_WEBHOOK_ID`), Live sin
`TALLERCLARO_ALLOW_LIVE_PAYMENTS=true` y un rol de base de datos superusuario o
con `DELETE`.

No incluir secretos en el código ni en variables `VITE_*`.

## PostgreSQL

El esquema fuente de verdad está en [`database/schema.sql`](../database/schema.sql).
Incluye 001–002, la columna de reserva de 003, las tablas de 005–006 y
`evento_paypal` de 008 al crear tablas nuevas. Las columnas de idempotencia de
pago y sus índices únicos requieren la migración 007. En bases existentes, `CREATE TABLE IF NOT EXISTS`
no añade columnas: aplica cada migración por separado antes del despliegue, con
autorización explícita. No hay runner automático; consulta
[`database/README.md`](../database/README.md).

Antes de aplicar una migración en el servidor desplegado, verifica de forma de solo lectura:

```bash
psql -h <host> -U <user> -d <db> -c "SELECT version();"
psql -h <host> -U <user> -d <db> -c "\dt tallerclaro.*"
psql -h <host> -U <user> -d <db> -c "\d tallerclaro.cotizacion"
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/verify_privileges.sql
```

`verify_privileges.sql` comprueba el rol efectivo, las tablas, los privilegios
`DELETE`, la columna de reserva de captura y posibles intentos de pago pendientes
duplicados. No escribe datos.

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
`TALLERCLARO_PAYPAL_BRAND_NAME` fija la marca mostrada en PayPal. El checkout se
configura con `user_action=PAY_NOW` y `shipping_preference=NO_SHIPPING`.

**Idempotencia de creación.** Antes de llamar a PayPal se guarda el intento
pendiente con `clave_idempotencia` y `huella_solicitud` (SHA-256 de pedido, tipo,
importe y moneda). La misma clave se envía como `PayPal-Request-Id`. Un POST
repetido con el mismo contenido devuelve el mismo intento y la misma orden; un
cambio de importe responde `409`. Pasada `PAYMENT_IDEMPOTENCY_WINDOW` (15 min),
el intento debe conciliarse o cancelarse. El índice único parcial
`(id_pedido, tipo) WHERE estado = 'pending'` impide duplicados en PostgreSQL.

**Captura y conciliación.** Antes de capturar se persiste
`pedido.captura_en_curso`. Otros pagos del pedido quedan bloqueados hasta
completar y guardar el intento reservado. El POST de captura lleva una clave
`PayPal-Request-Id` estable por orden PayPal. Tras una respuesta HTTP no exitosa
se consulta la orden y se valida una captura completada. `POST /sync` consulta el
estado real: no captura si la orden sigue `CREATED`; persiste la captura si ya
está `COMPLETED`; captura solo si está `APPROVED` y el intento local sigue
`pending`; cancela el intento si está `VOIDED`. Si un intento cancelado o fallido
aparece como `COMPLETED` en PayPal, `sync` acredita esa captura sin volver a
capturar. Un fallo de transporte mantiene la reserva porque el resultado es
incierto. `POST /cancel` es local, rechaza pagos completados y no libera una
reserva de captura en curso.

Un fallo de conexión, timeout o protocolo HTTP se normaliza a
`PAYMENT_PROVIDER_ERROR` (HTTP 502), sin exponer secretos ni excepciones HTTPX.
Los errores mantienen la reserva. La recuperación local se probó con dobles, y
la idempotencia del proveedor y la concurrencia real siguen pendientes de
validación en Sandbox/PostgreSQL.

**Webhook.** `POST /api/payments/webhook/paypal` recibe el evento sin token de
cliente y exige `TALLERCLARO_PAYPAL_WEBHOOK_ID`. El backend llama a
`/v1/notifications/verify-webhook-signature` de PayPal antes de tocar la base:
sin `verification_status=SUCCESS` responde `401` y no registra nada. Los eventos
se deduplican en `tallerclaro.evento_paypal` con `ON CONFLICT DO NOTHING`; una
reentrega procesada responde `200 {"status": "duplicate"}` y un fallo queda como
`failed` para que la siguiente entrega lo reintente. Solo los eventos
`CHECKOUT.ORDER.*` y `PAYMENT.CAPTURE.*` provocan conciliación; reembolsos y
disputas se registran como `ignored`. La conciliación vuelve a consultar a PayPal:
nunca se acredita un pago usando solo el cuerpo del webhook.

**Conciliación en segundo plano.** Con `TALLERCLARO_PAYPAL_MODE=sandbox|live` y
`TALLERCLARO_PAYMENT_RECONCILIATION_ENABLED=true`, el `lifespan` inicia un bucle
que consulta los intentos `pending` con orden de PayPal sin actividad durante
`TALLERCLARO_PAYMENT_RECONCILIATION_MIN_AGE_SECONDS` (por lotes de
`TALLERCLARO_PAYMENT_RECONCILIATION_BATCH_SIZE`, cada
`TALLERCLARO_PAYMENT_RECONCILIATION_INTERVAL_SECONDS`) y los reconcilia con la
misma lógica de `sync`. Cada pago usa su propia unidad de trabajo y un fallo no
detiene el lote ni libera una reserva incierta. La tarea se cancela al apagar la
aplicación.

**Estado financiero y bloqueo.** El pedido expone `financial_status` derivado de
los pagos completados: `unpaid`, `deposit_paid` o `paid`. No se puede cancelar
ni borrar un pedido con pagos completados o con una captura en curso; esos casos
requieren resolución manual (reembolso fuera de este release).

## Arquitectura

- `domain`: Python puro, entidades y reglas. No depende de FastAPI, Pydantic, ORM ni SDK.
- `application`: casos de uso e interfaces `Protocol` documentadas. Depende solo del dominio y de sus DTOs.
- `infrastructure`: repositorios PostgreSQL, integraciones de IA y pagos que implementan las interfaces. El procesador PayPal es una fachada sobre `paypal_transport.py` (HTTP/OAuth) y `paypal_parsing.py` (validación pura de respuestas). `infrastructure/security/workshop_auth.py` concentra bcrypt y la validación del hash usada en arranque y autenticación.
- `presentation/http`: routers, esquemas Pydantic, extracción de credenciales HTTP y autorización. Delega a los casos de uso; no calcula dinero.
- `bootstrap` y `main.py`: configuración, composición mediante factorías registrables y arranque.
- Los protocolos de repositorios, servicios, pagos y reserva de captura describen precondiciones, resultados, errores y semántica transaccional; los dobles de `tests/fakes.py` respetan las mismas firmas y la misma semántica de commit/rollback.

## Matriz de aceptación local S.O.L.I.D

Esta matriz documenta los criterios de la especificación SDD del refactor. Las
firmas son comprobaciones auxiliares; el comportamiento se verifica con los
escenarios enlazados. Las pruebas SQL usan cursores controlados, no un servidor:
no certifican constraints, ejecución SQL ni concurrencia real de PostgreSQL.

| ID | Implementación | Evidencia local |
| --- | --- | --- |
| S1 | `Order` centraliza pagado, saldo, importe solicitado y elegibilidad; aplicación coordina | [Reglas monetarias](tests/domain/test_payment_rules.py), [captura](tests/application/test_capture_contract.py) |
| S2 | PayPal separa fachada, transporte y parsers puros | [Parsing](tests/unit/test_paypal_parsing.py), [fallos de transporte](tests/unit/test_paypal_transport_errors.py) |
| S3 | `workshop_auth.py` concentra bcrypt para arranque y autenticación | [Autenticación](tests/unit/test_workshop_auth_hash.py), [arranque](tests/unit/test_database_startup.py) |
| S4 | `WorkshopFinancialSummary` agrega importes en dominio y `AccountingFactsFormatter` formatea texto sin I/O | [Resumen financiero](tests/domain/test_financial_summary.py), [asistente contable](tests/unit/test_accounting_service.py) |
| O1 | Registros de factorías de IA y pagos con dependencias inyectadas | [Extensión de factorías](tests/unit/test_factory_registration.py) |
| O2 | Registro de factorías de asistente contable (`build_accounting_assistant`) | [Servicio contable](tests/unit/test_accounting_service.py) |
| L1 | Errores de transporte normalizados; repositorios del UoW se resuelven solo en contexto; tokens con reloj y vencimiento | [UoW](tests/unit/test_unit_of_work_contract.py), [tokens](tests/unit/test_customer_token_contract.py), [repositorios](tests/unit/test_repository_contracts.py), [HTTP 502](tests/api/test_payments.py) |
| I1 | `CaptureReservationRepository` separado de pedidos; contratos sin lookup de pago no consumido | [Reservas](tests/unit/test_capture_reservation_contract.py), [firmas auxiliares](tests/unit/test_protocol_conformance.py) |
| I2 | `AccountingAssistant` segregado de `AIService` para explicaciones de finanzas | [Firmas de protocolo](tests/unit/test_protocol_conformance.py) |
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
