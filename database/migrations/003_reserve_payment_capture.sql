BEGIN;
ALTER TABLE tallerclaro.pedido ADD COLUMN IF NOT EXISTS captura_en_curso bigint;
COMMIT;
