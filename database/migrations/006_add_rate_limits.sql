-- Migracion 006: límites de uso persistentes y atómicos.
-- Ejecutar en Supabase SQL Editor con autorizacion explicita.
--
-- El contador se incrementa con INSERT ... ON CONFLICT DO UPDATE, de modo que
-- dos peticiones concurrentes no pueden saltarse el límite. No se usa DELETE:
-- el rol tallerclaro_app solo tiene SELECT/INSERT/UPDATE.

BEGIN;

CREATE TABLE IF NOT EXISTS tallerclaro.limite_consumo (
    clave           text NOT NULL,
    ventana_inicio  timestamptz NOT NULL,
    contador        integer NOT NULL DEFAULT 0,
    expira_en       timestamptz NOT NULL,

    CONSTRAINT pk_limite_consumo PRIMARY KEY (clave, ventana_inicio),
    CONSTRAINT ck_limite_consumo_contador CHECK (contador >= 0),
    CONSTRAINT ck_limite_consumo_ventana CHECK (expira_en > ventana_inicio)
);

COMMENT ON TABLE tallerclaro.limite_consumo IS
    'Contadores atómicos por clave y ventana para limitar abuso.';
COMMENT ON COLUMN tallerclaro.limite_consumo.expira_en IS
    'Fin de la ventana; se usa para calcular Retry-After.';

CREATE INDEX IF NOT EXISTS ix_limite_consumo_expiracion
    ON tallerclaro.limite_consumo (expira_en);

DO $permisos$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tallerclaro_app') THEN
        GRANT SELECT, INSERT, UPDATE ON TABLE tallerclaro.limite_consumo TO tallerclaro_app;
    END IF;
END;
$permisos$;

COMMIT;
