# Directrices de Desarrollo de TallerClaro

## 1. Gestores de Paquetes y Entornos

- **Frontend (`frontend/`)**: Usar exclusivamente **`pnpm`** (`pnpm run dev`, `pnpm run lint`, `pnpm run build`, `pnpm install`). Nunca usar `npm` o `yarn`.
- **Backend (`Backend/`)**: Python 3.14 con **`uv`** y `"fastapi[standard]"` en `Backend/.venv` (`uv pip install -e '.[dev]'`, `fastapi dev src/tallerclaro/main.py`, pruebas con `.venv/bin/pytest`).

## 2. Infraestructura y Servicios (VPS con Coolify)

- **Base de Datos (PostgreSQL)**: La base de datos reside / se desplegará en un **servidor VPS administrado con Coolify**.
  - El agente **nunca** debe intentar levantar contenedores Docker o servicios locales de PostgreSQL.
  - La conexión del backend se realiza vía variables de entorno (`.env`) apuntando a dicha instancia remota de Coolify.
- **Pruebas de Backend**: Ejecutar siempre las pruebas en memoria existentes (`Backend/tests/`), las cuales usan dobles/fakes y no requieren conexión de red a la base de datos remota.
- **PayPal**: La integración de PayPal Sandbox se gestionará con sus credenciales de prueba; no simular pagos confirmados por servidor sin la API real.
- **Proveedor de IA**: La generación real de cotizaciones requiere credenciales configuradas por entorno (`TALLERCLARO_AI_API_KEY`). Las pruebas con `FakeAIService` o clientes HTTP simulados validan solo la lógica local, no la integración real.
- **Criterio para Cerrar Issues en GitHub**: **Nunca cerrar una issue** que dependa de servicios o credenciales externas (PostgreSQL en Coolify, API de IA o PayPal Sandbox) cuando solo haya sido probada con mocks/dobles en memoria. En esos casos, dejar la issue abierta y documentar en un comentario qué quedó listo en `main` y qué credencial/prueba en vivo falta para cerrarla.

## 3. Arquitectura del Backend (FastAPI Layered Monolith)

- El backend sigue una **arquitectura sencilla por capas (layered monolith)** con el patrón **Unit of Work (UoW) + Repository**:
  - `presentation/`: Routers HTTP con FastAPI, esquemas Pydantic (`extra="forbid"`), dependencias de autenticación y manejadores globales de excepciones. **Cero consultas SQL, cero conexiones de BD y cero lógica de negocio en routers.**
  - `application/`: Casos de uso (`use_cases/`), DTOs (`dataclasses`) y puertos `typing.Protocol` (`UnitOfWork`, `AIService`, `PaymentProcessor`). Es la única capa que define límites transaccionales (`with self._uow:`).
  - `domain/`: Entidades puras, objetos de valor (`Money` con `Decimal` y `ROUND_HALF_UP`), transiciones de estado e invariantes de negocio. **Cero dependencias de FastAPI, Pydantic, `psycopg` o `httpx`.**
  - `infrastructure/`: Implementaciones concretas (`PostgresUnitOfWork`, `Postgres*Repository`, adaptadores HTTP de IA y PayPal, `CustomerTokenService`).
  - `bootstrap/` y `main.py`: Configuración (`pydantic-settings`) y composición de dependencias.
- No etiquetar esta arquitectura como "hexagonal" ni sobre-complejizar la nomenclatura técnica.

## 4. Criterios de Aceptación y Auditoría Técnica Estricta

Antes de dar por terminada cualquier tarea o validar código (propio o de subagentes), no basta con que `pytest` o `pnpm run build` pasen. El agente debe auditar y garantizar estas **6 invariantes**:

1. **Alcance por Petición (*Request-Scoped*) y Seguridad del `UnitOfWork`**:
   - `app.state` solo debe almacenar el pool (`Database`) y una fábrica (`uow_factory` callable) que cree un `UnitOfWork` nuevo por petición; **nunca compartir una instancia mutable de `UnitOfWork`** entre peticiones concurrentes.
   - `PostgresUnitOfWork` debe apilar sus frames de conexión para que, si se anidan o intercalan bloques `with uow:`, jamás se sobrescriba una conexión activa ni quede una conexión sin devolver a `put_connection()`.
   - Al salir de `__exit__`, toda transacción donde hubo excepción o no se llamó explícitamente a `commit()` debe ejecutar `rollback()` antes de regresar la conexión al pool (evitando conexiones `IDLE IN TRANSACTION` en `psycopg`).

2. **Aislamiento Secuencial de Llamadas Externas (Prohibido Red dentro de Transacciones SQL)**:
   - **Nunca** ejecutar llamadas HTTP externas (IA o PayPal) dentro de un bloque `with self._uow:` abierto, ya que retiene conexiones del pool y bloqueos en PostgreSQL durante segundos de latencia de red (*connection starvation*).
   - Aplicar siempre el patrón en **3 fases**:
     1. *Fase 1 (Lectura/Validación)*: Abrir `with self._uow:`, validar existencia/estado de la entidad y salir del bloque para liberar la conexión.
     2. *Fase 2 (I/O Externo)*: Llamar a `AIService` o `PaymentProcessor` **fuera** de cualquier transacción de BD.
     3. *Fase 3 (Reconciliación/Commit)*: Abrir un nuevo `with self._uow:`, recargar la entidad para verificar que su estado siga siendo válido, aplicar los cambios de dominio, guardar en el repositorio y ejecutar `self._uow.commit()`.

3. **Verificación Financiera Estricta en Pagos (`CapturePayment`)**:
   - Al capturar un pago en PayPal, el caso de uso debe contrastar explícitamente la respuesta del proveedor contra el `Payment` esperado antes de acreditarlo:
     - `captured.status == "completed"`
     - `captured.paypal_order_id == payment.paypal_order_id`
     - `captured.currency == payment.currency` (`"USD"`)
     - `Money(Decimal(str(captured.amount))).amount == payment.amount.amount`
     - `captured.paypal_capture_id` presente y no vacío.
   - Cualquier discrepancia debe lanzar `ConflictError` y abortar la acreditación.

4. **Paridad Total entre Entidades de Dominio, Dobles en Memoria y Repositorios SQL**:
   - Todo campo de dominio (`Quote.assumptions`, `Quote.missing_info`, `Quote.line_items`, etc.) debe guardarse y leerse tanto en `Fake*Repository` como en `Postgres*Repository`.
   - Cuando una cotización reduzca sus partidas o pase a `needs_information` (`line_items = []`), el repositorio SQL debe desactivar las partidas sobrantes (`UPDATE ... SET activo = false`), respetando que el rol `tallerclaro_app` solo tiene permisos `SELECT/INSERT/UPDATE` (nunca `DELETE`).

5. **Prohibido el Monkey-Patching entre Capas**:
   - La capa `presentation/` nunca debe inyectar métodos mágicos ni mutar clases de `application/` o `domain/` en tiempo de ejecución.

6. **Higiene del Repositorio y Documentación**:
   - No dejar archivos internos de orquestación (`PROJECT.md`, `.agents/`) en la raíz ni documentar nombres de migraciones o comandos (`npm` en vez de `pnpm`) que no coincidan exactamente con el árbol de archivos real.
