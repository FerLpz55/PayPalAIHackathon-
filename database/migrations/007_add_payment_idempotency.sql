-- Migracion 007: idempotencia de pagos y orden del proveedor.
-- Ejecutar en Supabase SQL Editor con autorizacion explicita.
--
-- Objetivo:
--   * Guardar la clave de idempotencia enviada a PayPal y la huella de la
--     solicitud original para poder reintentar sin duplicar ordenes.
--   * Guardar la URL de aprobacion para reanudar un checkout ya creado.
--   * Garantizar como maximo un intento pendiente por pedido y tipo.
--
-- No se usa DELETE: el rol tallerclaro_app solo tiene SELECT/INSERT/UPDATE.

BEGIN;

ALTER TABLE tallerclaro.pago
    ADD COLUMN IF NOT EXISTS clave_idempotencia text;
ALTER TABLE tallerclaro.pago
    ADD COLUMN IF NOT EXISTS huella_solicitud text;
ALTER TABLE tallerclaro.pago
    ADD COLUMN IF NOT EXISTS paypal_approval_url text;

DO $restricciones$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_pago_clave_idempotencia_no_vacia'
    ) THEN
        ALTER TABLE tallerclaro.pago
            ADD CONSTRAINT ck_pago_clave_idempotencia_no_vacia
            CHECK (clave_idempotencia IS NULL OR btrim(clave_idempotencia) <> '');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_pago_huella_solicitud_no_vacia'
    ) THEN
        ALTER TABLE tallerclaro.pago
            ADD CONSTRAINT ck_pago_huella_solicitud_no_vacia
            CHECK (huella_solicitud IS NULL OR btrim(huella_solicitud) <> '');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_pago_approval_url_no_vacia'
    ) THEN
        ALTER TABLE tallerclaro.pago
            ADD CONSTRAINT ck_pago_approval_url_no_vacia
            CHECK (paypal_approval_url IS NULL OR btrim(paypal_approval_url) <> '');
    END IF;
END;
$restricciones$;

-- Normalizacion previa: deja un solo intento pendiente por pedido y tipo.
-- Los intentos antiguos se marcan como cancelados, no se borran.
WITH ranked AS (
    SELECT id_pago,
           row_number() OVER (
               PARTITION BY id_pedido, tipo
               ORDER BY fecha_creacion DESC, id_pago DESC
           ) AS position
    FROM tallerclaro.pago
    WHERE estado = 'pending'
)
UPDATE tallerclaro.pago AS payment
SET estado = 'cancelled'
FROM ranked
WHERE payment.id_pago = ranked.id_pago
  AND ranked.position > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_clave_idempotencia
    ON tallerclaro.pago (clave_idempotencia)
    WHERE clave_idempotencia IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_pendiente_por_pedido_tipo
    ON tallerclaro.pago (id_pedido, tipo)
    WHERE estado = 'pending';

COMMENT ON COLUMN tallerclaro.pago.clave_idempotencia IS
    'Clave enviada como PayPal-Request-Id para deduplicar reintentos.';
COMMENT ON COLUMN tallerclaro.pago.huella_solicitud IS
    'SHA-256 de pedido, tipo, importe y moneda de la solicitud original.';
COMMENT ON COLUMN tallerclaro.pago.paypal_approval_url IS
    'Enlace de aprobacion devuelto por PayPal para reanudar el checkout.';

COMMIT;
