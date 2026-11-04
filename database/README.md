# Base de datos — PostgreSQL (Supabase)

Directorio central para el esquema SQL y los archivos relacionados con PostgreSQL
(Supabase) de TallerClaro.

## Estado actual

- [x] Esquema inicial y actualización del esquema existente en `schema.sql`.
- [x] Datos de demostración en `seeds/demo.sql`.
- [x] Pruebas de aceptación del esquema en `tests/schema_test.sql`.
- [x] Conexión con FastAPI y repositorios PostgreSQL compatibles con Supabase Pooler (Supavisor).
- [x] Migraciones numeradas en `migrations/`.
- [ ] Verificar permisos y esquema del PostgreSQL en Supabase; verificar IA/PayPal.

## Organización

```text
database/
  README.md                 este archivo
  schema.sql                inicializacion y actualizacion del esquema tallerclaro
  seeds/demo.sql            datos ficticios de ejemplo
  tests/schema_test.sql     pruebas SQL que revierten sus datos al finalizar
  migrations/               cambios posteriores numerados
    001_add_customer_link_tokens.sql
    002_add_quote_clarification_fields.sql
```

`schema.sql` incorpora las migraciones 001 y 002 y puede ejecutarse en un
proyecto nuevo de Supabase o sobre el esquema inicial existente. No sustituye
futuras migraciones numeradas ni comprueba automáticamente todas las diferencias
de un esquema modificado manualmente.

## Requisitos

- Proyecto en **Supabase** (PostgreSQL 15+) o PostgreSQL 15–18 compatible.
- SQL Editor de Supabase o cliente `psql` disponible.

## Esquema

- Base: en Supabase la base por defecto es `postgres`.
- Esquema dedicado: `tallerclaro` (aislado de `public` y de PostgREST / Data API).
- Seis tablas de negocio (`cliente`, `carpintero`, `cotizacion`,
  `detalle_cotizacion`, `pedido`, `pago`) y `cliente_token`.
- Convenciones: columnas en español, `snake_case`, PK `bigint GENERATED ALWAYS AS
  IDENTITY`, importes `numeric(14,2)`, cantidades `numeric(12,3)`, moneda `USD`,
  fechas `timestamptz`, estados como `text` con `CHECK`, nombres calificados.

### Cambios respecto al diagrama original

- `email` se normalizo a `correo` en `cliente` y `carpintero`.
- Se agregaron `moneda` en `cotizacion`, `pedido` y `pago`.
- Se agregaron `ultima_actualizacion` en `cotizacion`, `pedido` y `pago`;
  `fecha_creacion` en `pago`.
- Se agrego `paypal_capture_id` en `pago`.
- `cotizacion.monto_total` y `cotizacion.descripcion` son NULL en borradores.
- `pago.fecha_pago` es NULL hasta que la captura se confirma.
- `pedido` usa una FK compuesta `(id_cotizacion, id_carpintero)` para garantizar
  que el pedido pertenezca al mismo carpintero de la cotizacion.

## Inicializar en Supabase (Recomendado)

1. Crea un proyecto en Supabase y abre el **SQL Editor** (o conéctate mediante `psql` usando el URI del **Session Pooler** en el puerto `5432`).
2. Ejecuta el contenido de `database/schema.sql`.
3. (Opcional) Ejecuta `database/seeds/demo.sql` para cargar los talleres y datos de demostración.
4. En el **Table Editor** de Supabase, selecciona el esquema `tallerclaro` en el desplegable superior izquierdo para visualizar las tablas.

Con `psql` y tu `DATABASE_URL` de Supabase:

```bash
# Aplicar esquema
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql

# (Opcional) Cargar datos de demo
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/seeds/demo.sql

# (Opcional) Ejecutar pruebas de aceptación del esquema (hacen ROLLBACK al final)
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/schema_test.sql
```

No escribir contrasenas en el SQL ni en archivos versionados. `schema.sql` ya
contiene la transaccion; no combinarlo con `--single-transaction`.

## Roles y permisos

- **Supabase (`postgres`)**: al ejecutar `schema.sql` en Supabase, el script
  revoca automáticamente cualquier privilegio de `PUBLIC` y de los roles de la
  Data API de Supabase (`anon`, `authenticated`) sobre el esquema `tallerclaro`,
  sus tablas y secuencias. Además, al no estar en `public`, PostgREST no expone
  las tablas públicamente.
- **`tallerclaro_app` (opcional)**: si decides crear un rol dedicado con `LOGIN`
  (`CREATE ROLE tallerclaro_app LOGIN PASSWORD '...'`), `schema.sql` detecta su
  existencia y le concede únicamente `USAGE` del esquema, `SELECT/INSERT/UPDATE`
  sobre las siete tablas y `USAGE` en sus secuencias identity (sin `DELETE`,
  `CREATE` ni `TRUNCATE`). Este rol SQL no sustituye la autorización de acceso
  por carpintero o token de cliente en FastAPI.

## Integracion con el backend

Los repositorios y modelos de persistencia Python viven en
`Backend/src/tallerclaro/infrastructure/`. El dominio y los casos de uso
permanecen independientes de PostgreSQL y del ORM.

Proporcionar las credenciales mediante configuracion local (`Backend/.env`) o
variables de entorno (`DATABASE_URL`). No guardar contrasenas, cadenas de
conexion reales, dumps ni copias de seguridad en Git. Las plantillas de
configuracion deben contener unicamente valores ficticios.

## Migraciones

`schema.sql` incluye las migraciones 001 y 002. Para inicializar o actualizar
el esquema en Supabase, puedes pegarlo en el SQL Editor o ejecutarlo con `psql`.
La ejecución es transaccional.

No ejecutes la migración 001 después de aplicar `schema.sql`: su `CREATE TABLE`
no es repetible. La migración 002 ya está incorporada. Conserva las migraciones
para bases inicializadas antes de esta actualización; los cambios posteriores
seguirán en archivos numerados.

Ejemplo de aplicación por CLI:

```bash
psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql
```

## Verificación antes de aplicar migraciones

Antes de tocar el PostgreSQL desplegado en Supabase, comprueba de forma de solo
lectura la versión, las tablas y el esquema:

```bash
# Versión del servidor
psql "$DATABASE_URL" -c "SELECT version();"

# Tablas del esquema tallerclaro
psql "$DATABASE_URL" -c "\dt tallerclaro.*"

# Estructura de una tabla
psql "$DATABASE_URL" -c "\d tallerclaro.cotizacion"

# Verificar si una migración ya fue aplicada
psql "$DATABASE_URL" -c \
  "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'tallerclaro' AND table_name = 'cliente_token');"
```

Nunca ejecutes migraciones ni pruebas que escriban contra la base desplegada sin
confirmar primero el entorno y tener un respaldo.
