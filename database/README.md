# Base de datos — PostgreSQL

Directorio central para el esquema SQL y los archivos relacionados con PostgreSQL
de TallerClaro.

## Estado actual

- [x] Esquema inicial implementado en `schema.sql`.
- [x] Datos de demostración en `seeds/demo.sql`.
- [x] Pruebas de aceptación del esquema en `tests/schema_test.sql`.
- [ ] Conexión con FastAPI.
- [ ] Migraciones numeradas para cambios posteriores.

## Organización

```text
database/
  README.md              este archivo
  schema.sql             definicion inicial del esquema tallerclaro
  seeds/demo.sql         datos ficticios de ejemplo
  tests/schema_test.sql  pruebas SQL que revierten sus datos al finalizar
```

Mantener una unica secuencia de cambios del esquema; no duplicarla en el backend.
La primera version del esquema ya esta versionada en `schema.sql`. Los cambios
futuros iran en migraciones numeradas; la primera migracion partira de esta base
sin duplicarla. No editar `schema.sql` para actualizar bases ya utilizadas.

## Requisitos

- PostgreSQL 18 o compatible.
- Cliente `psql` disponible.

## Esquema

- Base: `tallerclaro`.
- Esquema dedicado: `tallerclaro`.
- Seis tablas de negocio: `cliente`, `carpintero`, `cotizacion`,
  `detalle_cotizacion`, `pedido`, `pago`.
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

## Crear y ejecutar la base local (ejemplo)

```bash
# 1. Entrar como administrador
psql -h localhost -U postgres -d postgres

# 2. Crear rol propietario de desarrollo
CREATE ROLE tallerclaro_owner LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
\password tallerclaro_owner

# 3. Crear base
CREATE DATABASE tallerclaro OWNER tallerclaro_owner;
\q

# 4. Aplicar esquema
psql -X -h localhost -U tallerclaro_owner -d tallerclaro -v ON_ERROR_STOP=1 -f database/schema.sql

# 5. (Opcional) Cargar datos de demo
psql -X -h localhost -U tallerclaro_owner -d tallerclaro -v ON_ERROR_STOP=1 -f database/seeds/demo.sql

# 6. Crear base de pruebas y ejecutar pruebas de aceptacion
psql -h localhost -U postgres -d postgres -c "CREATE DATABASE tallerclaro_test OWNER tallerclaro_owner;"
psql -X -h localhost -U tallerclaro_owner -d tallerclaro_test -v ON_ERROR_STOP=1 -f database/schema.sql
psql -X -h localhost -U tallerclaro_owner -d tallerclaro_test -v ON_ERROR_STOP=1 -f database/tests/schema_test.sql
```

No escribir contrasenas en el SQL ni en URLs de conexion. `schema.sql` ya
contiene la transaccion; no combinarlo con `--single-transaction`.

## Roles y permisos

- `tallerclaro_owner`: propietario del esquema en desarrollo. Ejecuta
  `schema.sql` y concede permisos.
- `tallerclaro_app` (crear antes de conectar FastAPI): rol de aplicacion con
  `LOGIN`, sin privilegios administrativos. Conceder `USAGE` del esquema,
  `SELECT/INSERT/UPDATE` sobre las seis tablas y `USAGE` en las secuencias
  identity. No conceder `CREATE`, `DELETE`, `TRUNCATE` ni propiedad de tablas.
  Este rol SQL no sustituye la autorizacion de acceso por carpintero en FastAPI.

## Integracion con el backend

Los repositorios y modelos de persistencia Python viviran en
`Backend/src/tallerclaro/infrastructure/`. El dominio y los casos de uso
permanecen independientes de PostgreSQL y del ORM.

Proporcionar las credenciales mediante configuracion local o variables de entorno.
No guardar contrasenas, cadenas de conexion reales, dumps, copias de seguridad
ni directorios de datos de PostgreSQL en Git. Las plantillas de configuracion
deben contener unicamente valores ficticios.

Consultar el [plan del backend](../docs/superpowers/plans/2026-10-31-fastapi-layers.md)
para la arquitectura y el alcance actual.
