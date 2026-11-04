# Directrices para agentes — TallerClaro

Monorepo de hackathon: frontend React 19 + Vite (`frontend/`), backend FastAPI por capas (`Backend/`) y PostgreSQL (`database/`). No hay CI ni gestor de tareas raíz; la verificación es local.

## Comandos verificados

Backend (desde `Backend/`; el `.venv` del repo usa Python 3.14 y `pyproject.toml` exige >=3.11):

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env                  # ajustar valores; .env está ignorado por git
fastapi dev src/tallerclaro/main.py   # API en http://127.0.0.1:8000, docs en /docs
.venv/bin/pytest                      # suite en memoria; no necesita PostgreSQL ni red
.venv/bin/pytest tests/application/test_use_cases.py::test_capture_payment_rejects_mismatched_amount_and_currency
```

Frontend (desde `frontend/`, usar **solo `pnpm`**, nunca `npm`/`yarn`):

```bash
pnpm install
pnpm run dev
pnpm run lint && pnpm run build      # no existe script de tests
```

`frontend/README.md` está desactualizado (recomienda `npm` y dice que no hay integración con API). El código real ya tiene modo demo/API; la fuente de verdad es `frontend/src/services/apiClient.js`, no ese README.

## Modo demo vs API real (frontend)

- El modo se decide únicamente por `VITE_API_BASE_URL`: vacío ⇒ `mockApi`/`localStorage`; no vacío ⇒ `fetch` a `/api`. `VITE_APP_MODE` aparece en el README raíz pero **no lo lee el código**.
- Demo persiste en la clave `localStorage` `tallerclaro.demo.v1`; la sesión (token de cliente, credenciales) en `sessionStorage` `tallerclaro.session.v1`.
- No hacer fallback silencioso a demo tras un error del backend: el error debe propagarse.
- Nunca poner secretos de IA/PayPal en variables `VITE_*`; viven solo en `Backend/.env`.

## Mapa del backend

- **Monolito por capas** (*layered monolith*, **no** arquitectura hexagonal): `src/tallerclaro/{domain,application,infrastructure,presentation,bootstrap}` + `main.py` (composición y `lifespan`).
- **Lectura obligatoria antes de evaluar o cambiar**: al trabajar sobre `Backend/` o `database/`, leer siempre `Backend/README.md` y `database/README.md` en el primer turno antes de emitir un diagnóstico o plan; nunca inferir patrones arquitectónicos solo por nombres de archivos (`ports.py`, `adapter.py`, ahora migrados a `interfaces.py`, `service.py`, `paypal_processor.py`).
- Tests: `Backend/tests/` usa dobles de `tests/fakes.py` y `TestClient` con `app.dependency_overrides` (`tests/api/conftest.py`). Comportamiento nuevo debe reflejarse en fakes y en repositorios Postgres.
- IA y PayPal por defecto en `none`; sin credenciales los servicios responden `SERVICE_UNAVAILABLE`. Los tests con fakes no validan integraciones reales.
- Los routers importan casos de uso; no hay ORM, los repositorios usan SQL directo con `psycopg`.

## Invariantes de arquitectura (auditar antes de cerrar una tarea)

1. **UoW por petición**: `app.state` guarda el pool (`Database`) y `uow_factory` (callable); nunca compartir una instancia mutable entre peticiones. No abrir `with uow:` en `presentation/` — la autorización delegada (p. ej. `VerifyCustomerToken`) sí puede abrirlo desde `application/`. `PostgresUnitOfWork` apila frames y devuelve siempre la conexión; `__exit__` hace `rollback()` si hubo excepción o no se llamó `commit()` (igual en `FakeUnitOfWork`).
2. **Cero red dentro de transacciones SQL**: las llamadas a IA/PayPal van *fuera* de `with self._uow:`. Patrón obligatorio en 3 fases: (1) abrir UoW, validar entidad/estado/`workshop_id` o token de cliente y salir; (2) llamar al proveedor externo; (3) abrir un UoW nuevo, recargar y revalidar, guardar y `commit()`.
3. **Captura de pagos estricta**: `PayPalPaymentProcessor.capture_order` debe leer `data["id"]`, exigir `purchase_units`/`captures` y `status == "COMPLETED"`. `CapturePayment` contrasta la respuesta con el `Payment` esperado (status, `paypal_order_id`, moneda USD, importe exacto con `Decimal`, `paypal_capture_id` no vacío), valida saldo pendiente y que no se duplique un anticipo; cualquier discrepancia lanza `ConflictError` sin acreditar.
4. **Paridad fake/Postgres**: todo campo de dominio (`assumptions`, `missing_info`, `line_items`, etc.) debe persistirse y leerse en ambos. Si una cotización queda sin partidas (`needs_information`), el repositorio SQL desactiva las sobrantes con `UPDATE ... SET activo = false`; el rol `tallerclaro_app` **no tiene `DELETE`**.
5. **Pureza de capas**: routers/dependencias no calculan dinero ni importan `Decimal`; todo cálculo monetario (USD, `ROUND_HALF_UP`) vive en `domain/`. Prohibido monkey-patching o mutar clases de `application/`/`domain/` desde `presentation/`.
6. **Higiene y seguridad**: no reintroducir `PROJECT.md`, `.agents/` ni planes internos en la raíz; no commitear archivos de configuración MCP (`mcp_config.json`, `*mcp*.json`), lockfiles de skills (`skills-lock.json`) ni tokens de acceso (`sbp_*`, `*.token`). No documentar comandos (`npm`) o migraciones que no existan en el árbol real.
7. **Convención de nombres por capas y S.O.L.I.D.**: no reintroducir `ports.py`, `adapter.py` ni terminología hexagonal. Las abstracciones de aplicación viven en `application/interfaces.py` y las implementaciones en `infrastructure/<area>/service.py` o `*_processor.py`. Mantener S.O.L.I.D. (SRP con parsers/validadores desacoplados de transporte, OCP con registries de factorías, ISP sin métodos muertos en protocolos y DIP inyectando dependencias abstractas).

## Base de datos e infraestructura

- **Supabase se usa SOLAMENTE como servidor PostgreSQL gestionado**: el backend FastAPI se conecta por SQL directo (`psycopg` + `DATABASE_URL`) al esquema dedicado `tallerclaro` (aislado de `public` y de PostgREST). No usar SDKs de Supabase (`supabase-py`, `@supabase/supabase-js`), Supabase Auth, PostgREST ni Edge Functions. No levantar contenedores Docker ni PostgreSQL local; no ejecutar escrituras, migraciones ni tests SQL contra la instancia desplegada sin confirmación explícita. Las verificaciones permitidas son de solo lectura (`SELECT version()`, `\dt`, `\d`).
- El pool de `psycopg` usa `prepare_threshold=None` y `wait(timeout=10)` para compatibilidad y tolerancia de latencia con Supavisor (Session Pooler de Supabase, puerto 5432, host según clúster asignado `aws-0` o `aws-1`); `PostgresUnitOfWork` aplica `SET LOCAL TRANSACTION ISOLATION LEVEL SERIALIZABLE` al abrir cada transacción.
- `database/schema.sql` es la base inicial (revoca permisos de `PUBLIC`, `anon` y `authenticated`, y aplica grants a `tallerclaro_app` de forma condicional si el rol existe); los cambios posteriores son migraciones SQL numeradas en `database/migrations/`. No hay runner de migraciones: se aplican desde el SQL Editor de Supabase o manualmente con `psql`.
- `database/seeds/demo.sql` es autocontenido e idempotente (crea esquema, tablas y triggers con `IF NOT EXISTS` si no fueron creados previamente e inserta datos demo con verificación previa y un `SELECT` de resumen para visualización en el SQL Editor). En Supabase Table Editor, seleccionar el esquema `tallerclaro` en el desplegable superior izquierdo para ver las tablas.

## Autorización y contrato HTTP

- Taller: Basic Auth (`require_workshop_credentials`) en listado/actualización de pedidos y generación de cotizaciones.
- Cliente: header `X-Customer-Token` (o `Authorization: Bearer`) en pagos. Lecturas/acciones de cotización y detalle de pedido usan `PrincipalDep` (token de cliente **o** Basic del taller).
- `frontend/docs/API_CONTRACT.md` es una foto del 2026-11-02 y contiene afirmaciones desactualizadas (p. ej. auth de cotizaciones); verificar contra los routers y esquemas actuales.

## Issues de GitHub

Nunca cerrar una issue que dependa de servicios/credenciales externas (PostgreSQL en Supabase, IA real o PayPal Sandbox) si solo se probó con mocks. Dejarla abierta y comentar qué quedó listo en `main` y qué prueba en vivo falta.
