-- Verificación de solo lectura del PostgreSQL de TallerClaro.
-- No crea, modifica ni borra objetos. Ejecutar con:
--   psql -X "$DATABASE_URL" -v ON_ERROR_STOP=1 -f database/tests/verify_privileges.sql
--
-- Sirve para confirmar, antes de aplicar migraciones o desplegar:
--   * el rol efectivo y si es superusuario;
--   * que el esquema y las tablas existen;
--   * que el rol de aplicación no puede borrar filas;
--   * si la migración 003 ya está aplicada;
--   * si hay intentos de pago pendientes duplicados que bloqueen la migración de idempotencia;
--   * si las columnas de idempotencia (007) y la tabla de webhooks (008) existen.

\echo '== Rol efectivo y versión =='
SELECT current_user AS effective_role,
       session_user AS session_role,
       current_setting('is_superuser') AS is_superuser,
       version() AS server_version;

\echo '== Esquema y tablas de negocio =='
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'tallerclaro'
ORDER BY table_name;

\echo '== Privilegios DELETE por tabla (debe estar vacío para tallerclaro_app) =='
SELECT c.relname AS table_name,
       has_table_privilege(current_user, c.oid, 'DELETE') AS can_delete
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'tallerclaro'
  AND c.relkind = 'r'
  AND has_table_privilege(current_user, c.oid, 'DELETE')
ORDER BY c.relname;

\echo '== Migración 003: columna de reserva de captura =='
SELECT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'tallerclaro'
      AND table_name = 'pedido'
      AND column_name = 'captura_en_curso'
) AS has_capture_reservation_column;

\echo '== Intentos de pago pendientes duplicados por pedido (debe estar vacío) =='
SELECT id_pedido, tipo, count(*) AS pending_attempts
FROM tallerclaro.pago
WHERE estado = 'pending'
GROUP BY id_pedido, tipo
HAVING count(*) > 1
ORDER BY id_pedido, tipo;

\echo '== Migración 007: columnas de idempotencia de pago =='
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'tallerclaro'
  AND table_name = 'pago'
  AND column_name IN ('clave_idempotencia', 'huella_solicitud', 'paypal_approval_url')
ORDER BY column_name;

\echo '== Migración 008: tabla de eventos de webhook =='
SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'tallerclaro'
      AND table_name = 'evento_paypal'
) AS has_paypal_event_table;
