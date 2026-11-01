-- TallerClaro - Esquema inicial de PostgreSQL
-- Proposito: definicion unica del esquema tallerclaro para una base nueva.
-- Version objetivo: PostgreSQL 18 (compatible con versiones recientes).
-- Instrucciones: ejecutar como usuario con permisos sobre la base tallerclaro.
--   psql -X -h localhost -U tallerclaro_owner -d tallerclaro -v ON_ERROR_STOP=1 -f database/schema.sql
-- Advertencia: este script NO contiene DROP ni TRUNCATE. Si se vuelve a ejecutar
-- sobre la misma base, fallara al crear el esquema y revertira la transaccion.

BEGIN;

SET LOCAL TIME ZONE 'UTC';

CREATE SCHEMA tallerclaro;

REVOKE ALL ON SCHEMA tallerclaro FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- 1. cliente
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.cliente (
    id_cliente              bigint GENERATED ALWAYS AS IDENTITY,
    nombre                  text NOT NULL,
    correo                  text NOT NULL,
    telefono                text,
    fecha_creacion          timestamptz NOT NULL DEFAULT now(),
    ultima_actualizacion    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_cliente PRIMARY KEY (id_cliente),
    CONSTRAINT ck_cliente_nombre_no_vacio CHECK (btrim(nombre) <> ''),
    CONSTRAINT ck_cliente_correo_no_vacio CHECK (btrim(correo) <> ''),
    CONSTRAINT ck_cliente_correo_normalizado CHECK (correo = lower(btrim(correo))),
    CONSTRAINT ck_cliente_telefono_no_vacio CHECK (telefono IS NULL OR btrim(telefono) <> '')
);

COMMENT ON TABLE tallerclaro.cliente IS 'Persona que solicita una cotizacion o encargo.';

-- ---------------------------------------------------------------------------
-- 2. carpintero
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.carpintero (
    id_carpintero   bigint GENERATED ALWAYS AS IDENTITY,
    nombre          text NOT NULL,
    nombre_taller   text NOT NULL,
    correo          text NOT NULL,
    telefono        text,
    fecha_creacion  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_carpintero PRIMARY KEY (id_carpintero),
    CONSTRAINT ck_carpintero_nombre_no_vacio CHECK (btrim(nombre) <> ''),
    CONSTRAINT ck_carpintero_nombre_taller_no_vacio CHECK (btrim(nombre_taller) <> ''),
    CONSTRAINT ck_carpintero_correo_no_vacio CHECK (btrim(correo) <> ''),
    CONSTRAINT ck_carpintero_correo_normalizado CHECK (correo = lower(btrim(correo))),
    CONSTRAINT ck_carpintero_telefono_no_vacio CHECK (telefono IS NULL OR btrim(telefono) <> '')
);

COMMENT ON TABLE tallerclaro.carpintero IS 'Artesano o taller que elabora los trabajos. No incluye autenticacion.';

-- ---------------------------------------------------------------------------
-- 3. cotizacion
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.cotizacion (
    id_cotizacion           bigint GENERATED ALWAYS AS IDENTITY,
    id_cliente              bigint NOT NULL,
    id_carpintero           bigint NOT NULL,
    solicitud               text NOT NULL,
    descripcion             text,
    monto_total             numeric(14,2),
    estado                  text NOT NULL DEFAULT 'draft',
    moneda                  text NOT NULL DEFAULT 'MXN',
    fecha_creacion          timestamptz NOT NULL DEFAULT now(),
    ultima_actualizacion    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT pk_cotizacion PRIMARY KEY (id_cotizacion),
    CONSTRAINT fk_cotizacion_cliente FOREIGN KEY (id_cliente)
        REFERENCES tallerclaro.cliente (id_cliente)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_cotizacion_carpintero FOREIGN KEY (id_carpintero)
        REFERENCES tallerclaro.carpintero (id_carpintero)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT uq_cotizacion_carpintero UNIQUE (id_cotizacion, id_carpintero),
    CONSTRAINT ck_cotizacion_solicitud_no_vacia CHECK (btrim(solicitud) <> ''),
    CONSTRAINT ck_cotizacion_descripcion_no_vacia CHECK (descripcion IS NULL OR btrim(descripcion) <> ''),
    CONSTRAINT ck_cotizacion_monto_total_no_nan CHECK (monto_total = monto_total),
    CONSTRAINT ck_cotizacion_monto_total_no_negativo CHECK (monto_total IS NULL OR monto_total >= 0),
    CONSTRAINT ck_cotizacion_estado CHECK (estado IN (
        'draft',
        'needs_information',
        'pending_review',
        'approved',
        'rejected'
    )),
    CONSTRAINT ck_cotizacion_moneda CHECK (moneda = 'MXN'),
    CONSTRAINT ck_cotizacion_datos_aprobacion CHECK (
        estado NOT IN ('pending_review', 'approved')
        OR (descripcion IS NOT NULL AND monto_total IS NOT NULL AND monto_total > 0)
    )
);

COMMENT ON TABLE tallerclaro.cotizacion IS 'Propuesta de trabajo entre un cliente y un carpintero.';
COMMENT ON COLUMN tallerclaro.cotizacion.monto_total IS 'Importe total en moneda de la cotizacion; NULL en borradores.';
COMMENT ON COLUMN tallerclaro.cotizacion.estado IS 'draft | needs_information | pending_review | approved | rejected.';

-- ---------------------------------------------------------------------------
-- 4. detalle_cotizacion
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.detalle_cotizacion (
    id_detalle          bigint GENERATED ALWAYS AS IDENTITY,
    id_cotizacion       bigint NOT NULL,
    tipo                text NOT NULL,
    descripcion         text NOT NULL,
    unidad              text NOT NULL,
    cantidad            numeric(12,3) NOT NULL,
    precio_unitario     numeric(14,2) NOT NULL,
    importe             numeric(14,2) GENERATED ALWAYS AS (
        round(cantidad * precio_unitario, 2)
    ) STORED,

    CONSTRAINT pk_detalle_cotizacion PRIMARY KEY (id_detalle),
    CONSTRAINT fk_detalle_cotizacion_cotizacion FOREIGN KEY (id_cotizacion)
        REFERENCES tallerclaro.cotizacion (id_cotizacion)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_detalle_cotizacion_tipo CHECK (tipo IN ('material', 'labor', 'other')),
    CONSTRAINT ck_detalle_cotizacion_descripcion_no_vacia CHECK (btrim(descripcion) <> ''),
    CONSTRAINT ck_detalle_cotizacion_unidad_no_vacia CHECK (btrim(unidad) <> ''),
    CONSTRAINT ck_detalle_cotizacion_cantidad_positiva CHECK (cantidad > 0 AND cantidad = cantidad),
    CONSTRAINT ck_detalle_cotizacion_precio_no_negativo CHECK (precio_unitario >= 0 AND precio_unitario = precio_unitario)
);

COMMENT ON TABLE tallerclaro.detalle_cotizacion IS 'Renglon de material, mano de obra u otro concepto de una cotizacion.';
COMMENT ON COLUMN tallerclaro.detalle_cotizacion.importe IS 'Calculado automaticamente: round(cantidad * precio_unitario, 2).';

-- ---------------------------------------------------------------------------
-- 5. pedido
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.pedido (
    id_pedido               bigint GENERATED ALWAYS AS IDENTITY,
    id_cotizacion           bigint NOT NULL,
    id_carpintero           bigint NOT NULL,
    codigo                  text NOT NULL,
    monto_total             numeric(14,2) NOT NULL,
    monto_anticipo          numeric(14,2) NOT NULL,
    moneda                  text NOT NULL DEFAULT 'MXN',
    estado                  text NOT NULL DEFAULT 'pending',
    fecha_creacion          timestamptz NOT NULL DEFAULT now(),
    ultima_actualizacion    timestamptz NOT NULL DEFAULT now(),
    fecha_entrega_estimada  date,

    CONSTRAINT pk_pedido PRIMARY KEY (id_pedido),
    CONSTRAINT fk_pedido_cotizacion_carpintero FOREIGN KEY (id_cotizacion, id_carpintero)
        REFERENCES tallerclaro.cotizacion (id_cotizacion, id_carpintero)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT uq_pedido_id_cotizacion UNIQUE (id_cotizacion),
    CONSTRAINT uq_pedido_codigo UNIQUE (codigo),
    CONSTRAINT ck_pedido_codigo_no_vacio CHECK (btrim(codigo) <> ''),
    CONSTRAINT ck_pedido_monto_total_positivo CHECK (monto_total > 0 AND monto_total = monto_total),
    CONSTRAINT ck_pedido_anticipo_no_negativo CHECK (monto_anticipo >= 0 AND monto_anticipo = monto_anticipo),
    CONSTRAINT ck_pedido_anticipo_no_superior_total CHECK (monto_anticipo <= monto_total),
    CONSTRAINT ck_pedido_moneda CHECK (moneda = 'MXN'),
    CONSTRAINT ck_pedido_estado CHECK (estado IN ('pending', 'paid', 'in_progress', 'delivered'))
);

COMMENT ON TABLE tallerclaro.pedido IS 'Encargo confirmado a partir de una cotizacion aprobada.';
COMMENT ON COLUMN tallerclaro.pedido.monto_total IS 'Importe acordado copiado de la cotizacion aprobada.';
COMMENT ON COLUMN tallerclaro.pedido.monto_anticipo IS 'Importe del anticipo exigido por politica de negocio.';
COMMENT ON COLUMN tallerclaro.pedido.estado IS 'pending | paid | in_progress | delivered.';

-- ---------------------------------------------------------------------------
-- 6. pago
-- ---------------------------------------------------------------------------
CREATE TABLE tallerclaro.pago (
    id_pago                 bigint GENERATED ALWAYS AS IDENTITY,
    id_pedido               bigint NOT NULL,
    tipo                    text NOT NULL,
    monto                   numeric(14,2) NOT NULL,
    moneda                  text NOT NULL DEFAULT 'MXN',
    estado                  text NOT NULL DEFAULT 'pending',
    paypal_order_id         text,
    paypal_capture_id       text,
    fecha_creacion          timestamptz NOT NULL DEFAULT now(),
    ultima_actualizacion    timestamptz NOT NULL DEFAULT now(),
    fecha_pago              timestamptz,

    CONSTRAINT pk_pago PRIMARY KEY (id_pago),
    CONSTRAINT fk_pago_pedido FOREIGN KEY (id_pedido)
        REFERENCES tallerclaro.pedido (id_pedido)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_pago_tipo CHECK (tipo IN ('deposit', 'balance')),
    CONSTRAINT ck_pago_monto_positivo CHECK (monto > 0 AND monto = monto),
    CONSTRAINT ck_pago_moneda CHECK (moneda = 'MXN'),
    CONSTRAINT ck_pago_estado CHECK (estado IN ('pending', 'completed', 'failed', 'cancelled')),
    CONSTRAINT ck_pago_paypal_order_id_no_vacio CHECK (paypal_order_id IS NULL OR btrim(paypal_order_id) <> ''),
    CONSTRAINT ck_pago_paypal_capture_id_no_vacio CHECK (paypal_capture_id IS NULL OR btrim(paypal_capture_id) <> ''),
    CONSTRAINT ck_pago_completed_exige_datos CHECK (
        estado <> 'completed'
        OR (paypal_order_id IS NOT NULL AND paypal_capture_id IS NOT NULL AND fecha_pago IS NOT NULL)
    ),
    CONSTRAINT ck_pago_no_completed_sin_datos CHECK (
        estado = 'completed'
        OR (paypal_capture_id IS NULL AND fecha_pago IS NULL)
    ),
    CONSTRAINT uq_pago_paypal_order_id UNIQUE (paypal_order_id),
    CONSTRAINT uq_pago_paypal_capture_id UNIQUE (paypal_capture_id)
);

COMMENT ON TABLE tallerclaro.pago IS 'Intento de pago asociado a un pedido.';
COMMENT ON COLUMN tallerclaro.pago.estado IS 'pending | completed | failed | cancelled.';
COMMENT ON COLUMN tallerclaro.pago.paypal_order_id IS 'ID de orden de PayPal; NULL si aun no se obtuvo respuesta.';
COMMENT ON COLUMN tallerclaro.pago.paypal_capture_id IS 'ID de captura de PayPal; obligatorio solo cuando estado = completed.';

-- ---------------------------------------------------------------------------
-- Indices adicionales
-- ---------------------------------------------------------------------------
CREATE INDEX ix_cotizacion_id_cliente ON tallerclaro.cotizacion (id_cliente);
CREATE INDEX ix_cotizacion_carpintero_fecha ON tallerclaro.cotizacion (id_carpintero, fecha_creacion DESC);
CREATE INDEX ix_detalle_cotizacion_id_cotizacion ON tallerclaro.detalle_cotizacion (id_cotizacion);
CREATE INDEX ix_pedido_carpintero_fecha ON tallerclaro.pedido (id_carpintero, fecha_creacion DESC);
CREATE INDEX ix_pago_id_pedido ON tallerclaro.pago (id_pedido);

-- ---------------------------------------------------------------------------
-- Funcion y triggers de ultima_actualizacion
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION tallerclaro.actualizar_timestamp()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    NEW.ultima_actualizacion := statement_timestamp();
    RETURN NEW;
END;
$$;

CREATE TRIGGER tr_cliente_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.cliente
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE TRIGGER tr_cotizacion_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.cotizacion
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE TRIGGER tr_pedido_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.pedido
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE TRIGGER tr_pago_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.pago
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

COMMIT;
