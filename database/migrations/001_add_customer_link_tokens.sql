-- TallerClaro - Migración 001: tokens de enlace de cliente
-- Almacena hashes de tokens de acceso temporal y su vencimiento.
-- No guardar tokens en texto plano; solo su hash.

BEGIN;

CREATE TABLE tallerclaro.cliente_token (
    id_token          bigint GENERATED ALWAYS AS IDENTITY,
    id_cliente        bigint NOT NULL,
    id_cotizacion     bigint NOT NULL,
    token_hash        text NOT NULL,
    fecha_expiracion  timestamptz NOT NULL,
    usado             boolean NOT NULL DEFAULT false,
    fecha_creacion    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_cliente_token PRIMARY KEY (id_token),
    CONSTRAINT fk_cliente_token_cliente FOREIGN KEY (id_cliente)
        REFERENCES tallerclaro.cliente (id_cliente)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_cliente_token_cotizacion FOREIGN KEY (id_cotizacion)
        REFERENCES tallerclaro.cotizacion (id_cotizacion)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT uq_cliente_token_hash UNIQUE (token_hash),
    CONSTRAINT ck_cliente_token_hash_no_vacio CHECK (btrim(token_hash) <> ''),
    CONSTRAINT ck_cliente_token_no_expirado_usado CHECK (
        usado = false OR fecha_expiracion >= now()
    )
);

COMMENT ON TABLE tallerclaro.cliente_token IS
    'Tokens de enlace de un solo uso para acceso temporal del cliente.';

CREATE INDEX ix_cliente_token_hash ON tallerclaro.cliente_token (token_hash);

COMMIT;
