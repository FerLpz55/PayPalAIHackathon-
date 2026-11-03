-- TallerClaro - Migración 002: supuestos, información faltante y estado activo de detalles
-- Agrega columnas en tallerclaro.cotizacion para persistir supuestos y preguntas aclaratorias de IA,
-- y columna activo en tallerclaro.detalle_cotizacion para desactivar partidas reemplazadas sin requerir DELETE.

BEGIN;

ALTER TABLE tallerclaro.cotizacion
    ADD COLUMN IF NOT EXISTS supuestos text[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS informacion_faltante text[] NOT NULL DEFAULT '{}';

COMMENT ON COLUMN tallerclaro.cotizacion.supuestos IS
    'Lista de supuestos generados por IA para la cotización.';
COMMENT ON COLUMN tallerclaro.cotizacion.informacion_faltante IS
    'Preguntas aclaratorias pendientes cuando estado = needs_information.';

ALTER TABLE tallerclaro.detalle_cotizacion
    ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN tallerclaro.detalle_cotizacion.activo IS
    'Indica si el renglón pertenece a la revisión vigente de la cotización.';

COMMIT;

