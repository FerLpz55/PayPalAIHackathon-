-- TallerClaro - Esquema e inicializacion completa con datos de demostracion.
--
-- Este script es autocontenido: puede ejecutarse directamente en una base limpia
-- de Supabase (SQL Editor) o sobre una base que ya tenga el esquema inicial.
--
-- Crea el esquema tallerclaro, las 7 tablas, triggers, indices, seguridad
-- y datos de prueba ficticios. Ademas es idempotente (no duplica registros).

BEGIN;

SET LOCAL TIME ZONE 'UTC';

-- ---------------------------------------------------------------------------
-- 0. Esquema dedicado tallerclaro
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS tallerclaro;

-- ---------------------------------------------------------------------------
-- 1. cliente
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tallerclaro.cliente (
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
CREATE TABLE IF NOT EXISTS tallerclaro.carpintero (
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
CREATE TABLE IF NOT EXISTS tallerclaro.cotizacion (
    id_cotizacion           bigint GENERATED ALWAYS AS IDENTITY,
    id_cliente              bigint NOT NULL,
    id_carpintero           bigint NOT NULL,
    solicitud               text NOT NULL,
    descripcion             text,
    monto_total             numeric(14,2),
    estado                  text NOT NULL DEFAULT 'draft',
    moneda                  text NOT NULL DEFAULT 'USD',
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
    CONSTRAINT ck_cotizacion_moneda CHECK (moneda = 'USD'),
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
CREATE TABLE IF NOT EXISTS tallerclaro.detalle_cotizacion (
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
CREATE TABLE IF NOT EXISTS tallerclaro.pedido (
    id_pedido               bigint GENERATED ALWAYS AS IDENTITY,
    id_cotizacion           bigint NOT NULL,
    id_carpintero           bigint NOT NULL,
    codigo                  text NOT NULL,
    monto_total             numeric(14,2) NOT NULL,
    monto_anticipo          numeric(14,2) NOT NULL,
    moneda                  text NOT NULL DEFAULT 'USD',
    estado                  text NOT NULL DEFAULT 'pending',
    fecha_creacion          timestamptz NOT NULL DEFAULT now(),
    ultima_actualizacion    timestamptz NOT NULL DEFAULT now(),
    fecha_entrega_estimada  date,
    captura_en_curso        bigint,

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
    CONSTRAINT ck_pedido_moneda CHECK (moneda = 'USD'),
    CONSTRAINT ck_pedido_estado CHECK (estado IN ('pending', 'paid', 'in_progress', 'delivered'))
);

COMMENT ON TABLE tallerclaro.pedido IS 'Encargo confirmado a partir de una cotizacion aprobada.';
COMMENT ON COLUMN tallerclaro.pedido.monto_total IS 'Importe acordado copiado de la cotizacion aprobada.';
COMMENT ON COLUMN tallerclaro.pedido.monto_anticipo IS 'Importe del anticipo exigido por politica de negocio.';
COMMENT ON COLUMN tallerclaro.pedido.estado IS 'pending | paid | in_progress | delivered.';

-- ---------------------------------------------------------------------------
-- 6. pago
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tallerclaro.pago (
    id_pago                 bigint GENERATED ALWAYS AS IDENTITY,
    id_pedido               bigint NOT NULL,
    tipo                    text NOT NULL,
    monto                   numeric(14,2) NOT NULL,
    moneda                  text NOT NULL DEFAULT 'USD',
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
    CONSTRAINT ck_pago_moneda CHECK (moneda = 'USD'),
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
-- 7. cliente_token (Migracion 001)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tallerclaro.cliente_token (
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

-- ---------------------------------------------------------------------------
-- 8. Campos adicionales de cotizacion y detalle (Migracion 002)
-- ---------------------------------------------------------------------------
ALTER TABLE tallerclaro.cotizacion
    ADD COLUMN IF NOT EXISTS supuestos text[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS informacion_faltante text[] NOT NULL DEFAULT '{}';

COMMENT ON COLUMN tallerclaro.cotizacion.supuestos IS
    'Lista de supuestos generados por IA para la cotizacion.';
COMMENT ON COLUMN tallerclaro.cotizacion.informacion_faltante IS
    'Preguntas aclaratorias pendientes cuando estado = needs_information.';

ALTER TABLE tallerclaro.detalle_cotizacion
    ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN tallerclaro.detalle_cotizacion.activo IS
    'Indica si el renglon pertenece a la revision vigente de la cotizacion.';

-- ---------------------------------------------------------------------------
-- 9. Indices
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_cotizacion_id_cliente ON tallerclaro.cotizacion (id_cliente);
CREATE INDEX IF NOT EXISTS ix_cotizacion_carpintero_fecha ON tallerclaro.cotizacion (id_carpintero, fecha_creacion DESC);
CREATE INDEX IF NOT EXISTS ix_detalle_cotizacion_id_cotizacion ON tallerclaro.detalle_cotizacion (id_cotizacion);
CREATE INDEX IF NOT EXISTS ix_pedido_carpintero_fecha ON tallerclaro.pedido (id_carpintero, fecha_creacion DESC);
CREATE INDEX IF NOT EXISTS ix_pago_id_pedido ON tallerclaro.pago (id_pedido);
CREATE INDEX IF NOT EXISTS ix_cliente_token_hash ON tallerclaro.cliente_token (token_hash);

-- ---------------------------------------------------------------------------
-- 10. Funcion y triggers de ultima_actualizacion
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

CREATE OR REPLACE TRIGGER tr_cliente_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.cliente
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE OR REPLACE TRIGGER tr_cotizacion_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.cotizacion
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE OR REPLACE TRIGGER tr_pedido_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.pedido
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

CREATE OR REPLACE TRIGGER tr_pago_actualizar_timestamp
    BEFORE UPDATE ON tallerclaro.pago
    FOR EACH ROW
    EXECUTE FUNCTION tallerclaro.actualizar_timestamp();

-- ---------------------------------------------------------------------------
-- 11. Seguridad y aislamiento en Supabase
-- ---------------------------------------------------------------------------
REVOKE ALL ON SCHEMA tallerclaro FROM PUBLIC;

DO $permisos$
DECLARE
    tabla text;
    columna text;
    secuencia text;
    rol_publico text;
BEGIN
    -- En Supabase, revocar cualquier acceso de los roles de Data API (anon, authenticated)
    FOREACH rol_publico IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = rol_publico) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA tallerclaro FROM %I', rol_publico);
            EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA tallerclaro FROM %I', rol_publico);
            EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA tallerclaro FROM %I', rol_publico);
        END IF;
    END LOOP;

    -- Si existe el rol dedicado tallerclaro_app, conceder privilegios minimos sin DELETE
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tallerclaro_app') THEN
        GRANT USAGE ON SCHEMA tallerclaro TO tallerclaro_app;
        GRANT SELECT, INSERT, UPDATE ON TABLE
            tallerclaro.cliente,
            tallerclaro.carpintero,
            tallerclaro.cotizacion,
            tallerclaro.detalle_cotizacion,
            tallerclaro.pedido,
            tallerclaro.pago,
            tallerclaro.cliente_token
        TO tallerclaro_app;

        FOR tabla, columna IN
            SELECT * FROM (VALUES
                ('cliente', 'id_cliente'),
                ('carpintero', 'id_carpintero'),
                ('cotizacion', 'id_cotizacion'),
                ('detalle_cotizacion', 'id_detalle'),
                ('pedido', 'id_pedido'),
                ('pago', 'id_pago'),
                ('cliente_token', 'id_token')
            ) AS ids(nombre_tabla, nombre_columna)
        LOOP
            secuencia := pg_get_serial_sequence(format('%I.%I', 'tallerclaro', tabla), columna);
            IF secuencia IS NOT NULL THEN
                EXECUTE format('GRANT USAGE ON SEQUENCE %s TO tallerclaro_app', secuencia);
            END IF;
        END LOOP;
    END IF;
END;
$permisos$;

-- ---------------------------------------------------------------------------
-- 12. Datos de demostracion ficticios (idempotentes)
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    v_id_carpintero_1 bigint;
    v_id_carpintero_2 bigint;
    v_id_cliente      bigint;
    v_id_cotizacion   bigint;
    v_id_pedido       bigint;
    v_codigo_pedido   text;
BEGIN
    -- Carpintero 1
    SELECT id_carpintero INTO v_id_carpintero_1
    FROM tallerclaro.carpintero
    WHERE correo = 'jose@martinez.example';

    IF v_id_carpintero_1 IS NULL THEN
        INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo, telefono)
        VALUES ('Jose Martinez', 'Carpinteria Martinez', 'jose@martinez.example', '5512345678')
        RETURNING id_carpintero INTO v_id_carpintero_1;
    END IF;

    -- Carpintero 2
    SELECT id_carpintero INTO v_id_carpintero_2
    FROM tallerclaro.carpintero
    WHERE correo = 'ana@lopez.example';

    IF v_id_carpintero_2 IS NULL THEN
        INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo, telefono)
        VALUES ('Ana Lopez', 'Madera y Diseno Lopez', 'ana@lopez.example', '5587654321')
        RETURNING id_carpintero INTO v_id_carpintero_2;
    END IF;

    -- Cliente
    SELECT id_cliente INTO v_id_cliente
    FROM tallerclaro.cliente
    WHERE correo = 'carlos@example.com';

    IF v_id_cliente IS NULL THEN
        INSERT INTO tallerclaro.cliente (nombre, correo, telefono)
        VALUES ('Carlos Ficticio', 'carlos@example.com', '5555555555')
        RETURNING id_cliente INTO v_id_cliente;
    END IF;

    -- Cotizacion
    SELECT id_cotizacion INTO v_id_cotizacion
    FROM tallerclaro.cotizacion
    WHERE id_cliente = v_id_cliente AND id_carpintero = v_id_carpintero_1;

    IF v_id_cotizacion IS NULL THEN
        INSERT INTO tallerclaro.cotizacion (
            id_cliente, id_carpintero, solicitud, descripcion,
            monto_total, estado, moneda
        )
        VALUES (
            v_id_cliente, v_id_carpintero_1,
            'Mesa de comedor de madera solida para 6 personas',
            'Mesa con patas torneadas y acabado barnizado. Incluye material y mano de obra.',
            350.00, 'approved', 'USD'
        )
        RETURNING id_cotizacion INTO v_id_cotizacion;

        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES
            (v_id_cotizacion, 'material', 'Madera de encino', 'pieza', 2.000, 100.00),
            (v_id_cotizacion, 'labor', 'Carpinteria y ensamble', 'servicio', 1.000, 150.00);
    END IF;

    -- Pedido
    SELECT id_pedido INTO v_id_pedido
    FROM tallerclaro.pedido
    WHERE id_cotizacion = v_id_cotizacion;

    IF v_id_pedido IS NULL THEN
        v_codigo_pedido := 'TC-' || replace(gen_random_uuid()::text, '-', '');

        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado, fecha_entrega_estimada
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero_1, v_codigo_pedido,
            350.00, 175.00, 'USD', 'pending', CURRENT_DATE + 14
        )
        RETURNING id_pedido INTO v_id_pedido;

        INSERT INTO tallerclaro.pago (
            id_pedido, tipo, monto, moneda, estado,
            paypal_order_id, paypal_capture_id, fecha_pago
        )
        VALUES (
            v_id_pedido, 'deposit', 175.00, 'USD', 'pending',
            NULL, NULL, NULL
        );
    END IF;

    RAISE NOTICE 'Demo preparado: cotizacion=%, pedido=%', v_id_cotizacion, v_id_pedido;
END;
$$;

COMMIT;

-- ---------------------------------------------------------------------------
-- 13. Resumen de confirmacion para visualizacion en Supabase SQL Editor
-- ---------------------------------------------------------------------------
SELECT
    'OK' AS estado_instalacion,
    (SELECT count(*) FROM tallerclaro.carpintero) AS carpinteros,
    (SELECT count(*) FROM tallerclaro.cliente) AS clientes,
    (SELECT count(*) FROM tallerclaro.cotizacion) AS cotizaciones,
    (SELECT count(*) FROM tallerclaro.pedido) AS pedidos,
    (SELECT count(*) FROM tallerclaro.pago) AS pagos;
