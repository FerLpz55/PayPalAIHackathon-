-- Migracion 004: Permitir estados 'cancelled' y 'deleted' en pedidos (tallerclaro.pedido)
-- Ejecutar en Supabase SQL Editor:

BEGIN;

ALTER TABLE tallerclaro.pedido
    DROP CONSTRAINT IF EXISTS ck_pedido_estado;

ALTER TABLE tallerclaro.pedido
    ADD CONSTRAINT ck_pedido_estado 
    CHECK (estado IN ('pending', 'paid', 'in_progress', 'delivered', 'cancelled', 'deleted'));

COMMENT ON COLUMN tallerclaro.pedido.estado IS 'pending | paid | in_progress | delivered | cancelled | deleted.';

COMMIT;
