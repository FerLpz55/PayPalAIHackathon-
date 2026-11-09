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
pnpm run test && pnpm run lint && pnpm run build
```

`pnpm run test` ejecuta la suite de Vitest (sin navegador ni backend).

`frontend/README.md` documenta modos y despliegue en Vercel; la fuente de verdad del modo sigue siendo `frontend/src/services/apiClient.js`.

## Modo demo vs API real (frontend)

- El modo se decide en `frontend/src/services/apiClient.js`: `VITE_APP_MODE=demo` ⇒ `mockApi`/`localStorage`; si no es demo y `VITE_API_BASE_URL` (solo origen, las rutas ya incluyen `/api`) no está vacío ⇒ `fetch` al backend; si no es demo y falta la URL, la app muestra "no configurado" y no enseña datos de ejemplo.
- Despliegue del frontend en Vercel (Root Directory `frontend`; install/build/salida y cabeceras de seguridad en `frontend/vercel.json`); pnpm fijado por `packageManager` + `pnpm-lock.yaml` versionado (requiere `ENABLE_EXPERIMENTAL_COREPACK=1` en Vercel), Node por `engines.node`. Las variables `VITE_*` se fijan en build.
- Demo persiste en la clave `localStorage` `tallerclaro.demo.v1`; la sesión (token de cliente, credenciales) en `sessionStorage` `tallerclaro.session.v1`.
- No hacer fallback silencioso a demo tras un error del backend: el error debe propagarse.
- Nunca poner secretos de IA/PayPal en variables `VITE_*`; viven solo en `Backend/.env`.

## Mapa del backend

- **Monolito por capas** (*layered monolith*, **no** arquitectura hexagonal): `src/tallerclaro/{domain,application,infrastructure,presentation,bootstrap}` + `main.py` (composición y `lifespan`).
- **Lectura obligatoria antes de evaluar o cambiar**: al trabajar sobre `Backend/` o `database/`, leer siempre `Backend/BACKENDREADME.md` y `database/README.md` en el primer turno antes de emitir un diagnóstico o plan; nunca inferir patrones arquitectónicos solo por nombres de archivos (`ports.py`, `adapter.py`, ahora migrados a `interfaces.py`, `service.py`, `paypal_processor.py`).
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

- Taller: sesión opaca con cookie `__Host-tallerclaro_session` (`HttpOnly`, `Secure`, `SameSite=Lax`, 30 min de inactividad / 8 h absolutas) en listado/actualización de pedidos y reemisión de acceso de cliente. Login/sesión/logout en `/api/auth/*`; toda petición autenticada por cookie que cambie estado exige `X-CSRF-Token` y `Origin` permitido. Basic solo se acepta con `TALLERCLARO_ENABLE_WORKSHOP_BASIC_AUTH=true`.
- Cliente: header `X-Customer-Token` (o `Authorization: Bearer`) en pagos y `GET /api/customer/context`. Lecturas/acciones de cotización, generación y detalle de pedido usan `PrincipalDep` (token del cliente propietario **o** sesión/Basic del taller); un token inválido nunca degrada a privilegios del taller.
- Reemitir el enlace del cliente es exclusivo del taller (`POST /api/quotes/{id}/customer-access`), revoca los tokens previos y audita el evento; no se recupera acceso solo con el ID.
- Límites persistentes: login 5 fallos/15 min por usuario e IP, creación 5/min por IP, generación 5/10 min por cotización y 100/h por taller, catálogo 20/min por actor. Responden `429` con `Retry-After`. Cuerpos JSON limitados a 64 KiB (`413`).
- `frontend/docs/API_CONTRACT.md` es una foto del 2026-11-02 y contiene afirmaciones desactualizadas (p. ej. auth de cotizaciones); verificar contra los routers y esquemas actuales.

## Contexto verificado el 2026-11-09 (fases A–C)

- `Backend/.env` se resuelve por ruta absoluta desde el paquete y las variables del proceso tienen prioridad; las pruebas neutralizan el archivo. `TALLERCLARO_ENVIRONMENT=release` rechaza secretos de plantilla, CORS con comodines/HTTP, PayPal incompleto y Live sin `TALLERCLARO_ALLOW_LIVE_PAYMENTS=true`.
- El pool usa `check_connection`, timeout de adquisición y `max_idle=300`; una indisponibilidad responde `503`. `uow.execute_sql` reintenta solo fases SQL ante `SERIALIZABLE`, nunca operaciones que llamaron a IA/PayPal. En release el rol no puede ser superusuario ni tener `DELETE`.
- Migraciones 005 (`sesion_taller`) y 006 (`limite_consumo`) existen pero **no se han aplicado** contra Supabase. `database/tests/verify_privileges.sql` es de solo lectura.
- Verificación local: 400 pruebas backend aprobadas con Python 3.14 (1 advertencia de `pytest-asyncio`); frontend sin cambios en esta fase. No se validaron PostgreSQL, IA ni PayPal reales.
- El frontend sigue usando `taller:demo-password` y credenciales en `sessionStorage`, y genera cotizaciones como ruta de taller; su migración a sesiones llega en la Fase F.

## Contexto histórico verificado el 2026-11-04 (parcialmente superado)

- El arranque exige hash bcrypt válido en `TALLERCLARO_WORKSHOP_PASSWORD_HASH` y conexión inicial a PostgreSQL. El backend no tiene contraseña de taller predeterminada. PayPal habilitado exige URL HTTPS en `TALLERCLARO_PAYPAL_RETURN_URL` y `TALLERCLARO_PAYPAL_CANCEL_URL`.
- La migración 003 añade `pedido.captura_en_curso`. Esquema y seed incluyen la columna para tablas nuevas; `CREATE TABLE IF NOT EXISTS` no actualiza una tabla existente. Verificar su presencia antes del despliegue.
- La reserva se confirma antes de llamar a PayPal y se libera al persistir la captura completada. Los errores mantienen el bloqueo para otros pagos del pedido.
- El procesador usa una clave de idempotencia estable por orden y consulta la orden tras un HTTP de captura no exitoso. Un timeout requiere reintentar el mismo pago. No hay conciliación en segundo plano ni herramienta de resolución manual.
- Las pruebas con dobles no demuestran capturas simultáneas en PostgreSQL ni idempotencia real de PayPal.
- El frontend aún usa credenciales guardadas o `taller:demo-password` para rutas de taller. Su flujo de cliente llama a generación protegida por Basic; documentar esta limitación y no habilitar credenciales demo en el backend como solución.
- Verificación local: 120 pruebas backend aprobadas y una advertencia de `pytest-asyncio`. TestClient se bloqueó en el sandbox y pasó fuera de él con pytest normal. No atribuir el bloqueo a plugins sin evidencia.

## Gestión de issues

Nunca cerrar una issue que dependa de servicios/credenciales externas (PostgreSQL en Supabase, IA real o PayPal Sandbox) si solo se probó con mocks. Dejarla abierta y comentar qué quedó listo en `main` y qué prueba en vivo falta.

## Flujo de ramas, Pull Requests e higiene en Git

1. **Aceptación de PRs que ya tuvieron commits intermedios**:
   - Usar `--merge` (evitar `--squash` y `--rebase`) para no generar SHAs divergentes en commits que ya fueron sincronizados o referenciados en otras ramas de trabajo.
2. **Registro de ancestros tras refactors estructurales**:
   - Cuando se integra código de una rama externa que fue adaptado manualmente tras una reestructuración de directorios (evitando conflictos falsos de git), enlazar la historia registrando el commit original como padre (`git merge -s ours <rama>`) para que GitHub cierre la PR limpiamente sin mostrar estado `CONFLICTING`.
3. **Preservación y re-sincronización de ramas colaborativas activas**:
   - Si una rama de feature pertenece a otro miembro del equipo con quien se continuará trabajando (p. ej. `feat/asistente-contable`), **nunca eliminarla** tras cerrar su PR. En su lugar, actualizar la rama remota (`git push origin <base>:<rama-feature>`) para que el colaborador pueda hacer `git pull` sin conflictos y continuar sobre la arquitectura más reciente.
4. **Limpieza de ramas obsoletas**:
   - Conservar como ramas permanentes y activas únicamente `main`, `refactor` y las ramas de feature en desarrollo activo acordadas en el equipo (p. ej. `feat/asistente-contable`). Eliminar ramas remotas de features cerradas y ya fusionadas (`feat/issue-*`).
5. **Guardias de modo en Frontend (`isDemoMode`, `isConnectedMode`, `isConfigurationMissing`)**:
   - Toda integración en `frontend/` (páginas, adaptadores y componentes) debe contemplar explícitamente los 3 estados: `demo` (con `mockApi`), `real`/`connected` (con `fetch` y propagación de errores) y `unconfigured` (mostrando estado vacío sin filtrar datos mock). Nunca hacer fallback silencioso a mocks ante errores o configuración ausente.
