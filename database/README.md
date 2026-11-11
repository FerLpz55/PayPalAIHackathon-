# TallerClaro Database

PostgreSQL schema and operational notes for TallerClaro. Supabase is used only as a managed PostgreSQL host. The backend connects directly through psycopg and DATABASE_URL; this project does not use Supabase Auth, PostgREST, Edge Functions, or Supabase SDKs.

Database provisioning, migrations, seeds, and SQL acceptance tests were not run. The backend's 481 passing unit/API tests use fakes and do not prove PostgreSQL persistence or that a deployed database matches the checked-in schema.

## Contents

    database/
      schema.sql
      migrations/
        001_add_customer_link_tokens.sql
        002_add_quote_clarification_fields.sql
        003_reserve_payment_capture.sql
        004_add_cancelled_order_status.sql
      seeds/demo.sql
      tests/schema_test.sql

## Requirements

- PostgreSQL 15 or newer; Supabase is the documented managed service.
- Supabase SQL Editor or psql.
- Backend connection through a PostgreSQL URL, preferably the Supabase Session Pooler documented in the project guide.
- TLS for deployed database connections.

The current files are:

```text
database/
  README.md                 este archivo
  schema.sql                inicializacion y actualizacion del esquema tallerclaro
  seeds/demo.sql            datos ficticios de ejemplo
  tests/schema_test.sql     pruebas SQL que revierten sus datos al finalizar
  tests/verify_privileges.sql  verificación de solo lectura del rol y el esquema
  migrations/               cambios posteriores numerados
    001_add_customer_link_tokens.sql
    002_add_quote_clarification_fields.sql
    003_reserve_payment_capture.sql
    004_add_cancelled_order_status.sql
    005_add_workshop_sessions.sql
    006_add_rate_limits.sql
    007_add_payment_idempotency.sql
    008_add_paypal_webhook_events.sql
```

`schema.sql` incorpora 001–002, la columna de 003 y las tablas de 005–006 al
crear tablas nuevas. Sobre una base existente, `CREATE TABLE IF NOT EXISTS` no
añade columnas: aplica 003 por separado. Las tablas `sesion_taller` y
`limite_consumo` deben crearse con las migraciones 005 y 006. Las columnas de
idempotencia de pago (`clave_idempotencia`, `huella_solicitud`,
`paypal_approval_url`) y los índices únicos requieren la migración 007; antes de
crearlos, normaliza los intentos pendientes duplicados por pedido y tipo. La
tabla `evento_paypal` (webhooks deduplicados) requiere la migración 008. El
esquema no sustituye futuras migraciones ni comprueba automáticamente todas las
diferencias de una base modificada manualmente.

The backend uses schema tallerclaro rather than public. PostgREST/Data API is not part of the application architecture.

## Schema

The application tables include:

- Base: en Supabase la base por defecto es `postgres`.
- Esquema dedicado: `tallerclaro` (aislado de `public` y de PostgREST / Data API).
- Seis tablas de negocio (`cliente`, `carpintero`, `cotizacion`,
  `detalle_cotizacion`, `pedido`, `pago`), `cliente_token`,
  `sesion_taller` (sesiones opacas del taller, migración 005),
  `limite_consumo` (contadores de abuso, migración 006), las columnas de
  idempotencia de `pago` (migración 007) y `evento_paypal` (webhooks,
  migración 008).
- Convenciones: columnas en español, `snake_case`, PK `bigint GENERATED ALWAYS AS
  IDENTITY`, importes `numeric(14,2)`, cantidades `numeric(12,3)`, moneda `USD`,
  fechas `timestamptz`, estados como `text` con `CHECK`, nombres calificados.

Amounts use numeric columns in USD; timestamps use timestamptz. Foreign keys, unique constraints, status checks, and amount checks enforce database integrity. Quote detail rows can be marked inactive instead of physically deleted. The schema includes the current customer token, clarification, capture-reservation, and cancelled/deleted order state fields for a new database.

The customer token table stores a hash rather than the raw token. The API returns the plaintext token once when the quote is created. No email delivery or cross-device token recovery service is implemented.

## New database setup

Use an empty development/test database or a newly provisioned Supabase project. From the repository root, configure DATABASE_URL in your shell without committing its value, then apply the schema:

    psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/schema.sql

The schema creates the tallerclaro tables, functions, triggers, indexes and grants in a transaction. It revokes privileges from PUBLIC and, when present, Supabase roles anon and authenticated. If role tallerclaro_app exists, it grants USAGE on the schema, SELECT/INSERT/UPDATE on the seven tables, and sequence usage; it does not grant DELETE.

Optionally load sample data into a disposable database:

    psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/seeds/demo.sql

The seed contains fictitious demo records. Never use those records as production customer or financial data.

## Existing database migrations

There is no migration runner and no migration-history table. Track applied migrations in the deployment process. Do not apply every file blindly.

For an existing database:

### Aprovisionar el rol de aplicación sin secretos en scripts

No escribas contraseñas en SQL versionado ni en scripts. Crea el rol una sola
vez desde el SQL Editor de Supabase o con `psql` y asigna la contraseña de forma
interactiva:

```sql
CREATE ROLE tallerclaro_app LOGIN;
```

```bash
psql "$DATABASE_URL" -c "\password tallerclaro_app"
```

Después ejecuta `schema.sql` (o reaplica únicamente los `GRANT`) y verifica el
resultado con [`tests/verify_privileges.sql`](tests/verify_privileges.sql).
El backend rechaza el arranque en `TALLERCLARO_ENVIRONMENT=release` si el rol
efectivo es superusuario o conserva `DELETE` sobre alguna tabla de negocio.


1. Confirm the target environment and take an appropriate backup.
2. Use read-only queries to inspect PostgreSQL version, schema, columns, constraints, and existing token/payment data.
3. Compare the deployed schema against schema.sql and migrations 001-008.
4. Apply only missing, compatible migration files in order using the approved database-owner process.
5. Verify the resulting schema with read-only queries before deploying a backend that depends on the new fields.

Migration notes:

- 001 creates customer link-token storage and is not written as a repeatable migration. Do not rerun it if the table already exists.
- 002 adds quote assumptions/missing-information and active detail-line fields. These changes are also included in schema.sql for new databases.
- 003 adds pedido.captura_en_curso for capture reservation. CREATE TABLE IF NOT EXISTS does not add it to an existing pedido table; apply migration 003 if missing before deploying the matching backend.
- 004 expands the order status constraint to include cancelled and deleted; schema.sql contains the current constraint for new databases.
- 005 adds revocable workshop sessions.
- 006 adds persistent abuse-rate counters.
- 007 adds payment idempotency fields and unique pending-attempt indexes.
- 008 adds deduplicated PayPal webhook events.
- schema.sql includes the current shape needed for a new database. It is not a general schema-diff or migration tool for manually modified databases.

Do not apply migrations or seed data to a deployed database without explicit approval and a backup.

## Read-only inspection

These commands inspect a configured database and do not apply schema changes. Run them only after confirming that DATABASE_URL points to the intended environment:

    psql -X "$DATABASE_URL" -c "SELECT version();"
    psql -X "$DATABASE_URL" -c "\dt tallerclaro.*"
    psql -X "$DATABASE_URL" -c "\d tallerclaro.pedido"

These checks do not prove that all constraints, grants, triggers, or application behavior are correct.

## SQL acceptance test

database/tests/schema_test.sql contains acceptance checks that run in a transaction and roll back. It executes SQL and should only be run against an isolated disposable test database:

    psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/schema_test.sql

Do not run it against production or shared data. No SQL test was run for this documentation update.

## Backend database configuration

Settings live in Backend/src/tallerclaro/bootstrap/settings.py. Configure either DATABASE_URL (preferred; TALLERCLARO_DATABASE_URL is an alias) or the individual TALLERCLARO_DATABASE_HOST, PORT, NAME, USER, PASSWORD, and SSL_MODE fields. DATABASE_URL takes precedence over those fields. The backend pool defaults to min size 2 and max size 10.

For Supabase, the repository recommends a Session Pooler URL using port 5432 and sslmode=require. Put the actual connection string only in Backend/.env or the backend deployment environment. Never put it in frontend VITE_* variables or commit it.

The backend fails startup if PostgreSQL is unavailable. GET /api/health is an HTTP liveness check and does not test the database. The application uses a per-request unit of work and SERIALIZABLE transactions; it disables automatic prepared statements for Supavisor compatibility.

## Related documentation

- [Project setup and API overview](../README.md)
- [Backend configuration and routes](../Backend/BACKENDREADME.md)
- [Frontend REAL/DEMO modes](../frontend/README.md)
- [Repository instructions](../AGENTS.md)
