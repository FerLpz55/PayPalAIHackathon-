-- Migracion 008: registro idempotente de eventos de webhook de PayPal.
-- Ejecutar en Supabase SQL Editor con autorizacion explicita.
--
-- Cada entrega se identifica por el id de evento de PayPal. La insercion usa
-- ON CONFLICT DO NOTHING, de modo que una reentrega no se procesa dos veces.
-- No se usa DELETE: el rol tallerclaro_app solo tiene SELECT/INSERT/UPDATE.

BEGIN;

CREATE TABLE IF NOT EXISTS tallerclaro.evento_paypal (
    id_evento       text NOT NULL,
    tipo            text NOT NULL,
    estado          text NOT NULL DEFAULT 'received',
    resultado       text,
    recibido_en     timestamptz NOT NULL DEFAULT now(),
    procesado_en    timestamptz,

    CONSTRAINT pk_evento_paypal PRIMARY KEY (id_evento),
    CONSTRAINT ck_evento_paypal_id_no_vacio CHECK (btrim(id_evento) <> ''),
    CONSTRAINT ck_evento_paypal_tipo_no_vacio CHECK (btrim(tipo) <> ''),
    CONSTRAINT ck_evento_paypal_estado CHECK (
        estado IN ('received', 'processed', 'ignored', 'failed')
    )
);

COMMENT ON TABLE tallerclaro.evento_paypal IS
    'Eventos de webhook de PayPal recibidos, para deduplicacion y auditoria.';
COMMENT ON COLUMN tallerclaro.evento_paypal.estado IS
    'received | processed | ignored | failed.';
COMMENT ON COLUMN tallerclaro.evento_paypal.resultado IS
    'Resumen del resultado: pago conciliado, evento ignorado o error acotado.';

CREATE INDEX IF NOT EXISTS ix_evento_paypal_tipo_recibido
    ON tallerclaro.evento_paypal (tipo, recibido_en DESC);

DO $permisos$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tallerclaro_app') THEN
        GRANT SELECT, INSERT, UPDATE ON tallerclaro.evento_paypal TO tallerclaro_app;
    END IF;
END;
$permisos$;

COMMIT;
