-- TallerClaro - Pruebas de aceptacion del esquema
-- Ejecutar sobre una base nueva con el esquema ya aplicado.
-- El script revierte todos los datos al final; solo permanece el esquema.
--   psql -X -h localhost -U tallerclaro_owner -d tallerclaro_test -v ON_ERROR_STOP=1 -f database/tests/schema_test.sql

BEGIN;

CREATE TEMP TABLE test_vars (
    id_cliente          bigint,
    id_carpintero       bigint,
    id_carpintero_2     bigint,
    id_cotizacion       bigint,
    id_pedido           bigint,
    codigo_pedido       text
);

INSERT INTO test_vars DEFAULT VALUES;

-- ===========================================================================
-- Setup: flujo valido
-- ===========================================================================
DO $$
DECLARE
    v_id_cliente        bigint;
    v_id_carpintero     bigint;
    v_id_carpintero_2   bigint;
    v_id_cotizacion     bigint;
    v_id_pedido         bigint;
    v_codigo            text;
    v_total             numeric(14,2);
BEGIN
    INSERT INTO tallerclaro.cliente (nombre, correo)
    VALUES ('Cliente Prueba', 'cliente.prueba@example.com')
    RETURNING id_cliente INTO v_id_cliente;

    INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo)
    VALUES ('Carpintero Prueba', 'Taller Prueba', 'carpintero.prueba@example.com')
    RETURNING id_carpintero INTO v_id_carpintero;

    INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo)
    VALUES ('Otro Carpintero', 'Otro Taller', 'otro.prueba@example.com')
    RETURNING id_carpintero INTO v_id_carpintero_2;

    INSERT INTO tallerclaro.cotizacion (
        id_cliente, id_carpintero, solicitud, descripcion,
        monto_total, estado, moneda
    )
    VALUES (
        v_id_cliente, v_id_carpintero,
        'Mesa de centro a medida',
        'Mesa de centro con cajon, madera de pino.',
        350.00, 'approved', 'USD'
    )
    RETURNING id_cotizacion INTO v_id_cotizacion;

    INSERT INTO tallerclaro.detalle_cotizacion (
        id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
    )
    VALUES
        (v_id_cotizacion, 'material', 'Tablero de pino', 'pieza', 2.000, 100.00),
        (v_id_cotizacion, 'labor', 'Ensamble y acabado', 'servicio', 1.000, 150.00);

    SELECT monto_total INTO v_total
    FROM tallerclaro.cotizacion
    WHERE id_cotizacion = v_id_cotizacion;

    IF v_total <> 350.00 THEN
        RAISE EXCEPTION 'Caso valido: monto_total esperado 350.00, obtenido %', v_total;
    END IF;

    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');

    INSERT INTO tallerclaro.pedido (
        id_cotizacion, id_carpintero, codigo, monto_total,
        monto_anticipo, moneda, estado
    )
    VALUES (
        v_id_cotizacion, v_id_carpintero, v_codigo,
        350.00, 175.00, 'USD', 'pending'
    )
    RETURNING id_pedido INTO v_id_pedido;

    UPDATE test_vars SET
        id_cliente = v_id_cliente,
        id_carpintero = v_id_carpintero,
        id_carpintero_2 = v_id_carpintero_2,
        id_cotizacion = v_id_cotizacion,
        id_pedido = v_id_pedido,
        codigo_pedido = v_codigo;

    RAISE NOTICE 'Setup: flujo valido creado (cotizacion=%, pedido=%)', v_id_cotizacion, v_id_pedido;
END;
$$;

-- ===========================================================================
-- Caso: detalle_cotizacion con cantidad 0, negativa o NaN
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_fallos        integer := 0;
    v_esperados     integer := 3;
BEGIN
    SELECT id_cotizacion INTO v_id_cotizacion FROM test_vars;

    -- cantidad = 0
    BEGIN
        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES (v_id_cotizacion, 'material', 'x', 'u', 0.000, 10.00);
        RAISE EXCEPTION 'Caso cantidad cero: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            v_fallos := v_fallos + 1;
    END;

    -- cantidad negativa
    BEGIN
        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES (v_id_cotizacion, 'material', 'x', 'u', -1.000, 10.00);
        RAISE EXCEPTION 'Caso cantidad negativa: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            v_fallos := v_fallos + 1;
    END;

    -- cantidad NaN
    BEGIN
        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES (v_id_cotizacion, 'material', 'x', 'u', 'NaN'::numeric, 10.00);
        RAISE EXCEPTION 'Caso cantidad NaN: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            v_fallos := v_fallos + 1;
    END;

    IF v_fallos <> v_esperados THEN
        RAISE EXCEPTION 'Caso cantidad invalida: se esperaban % rechazos, se obtuvieron %', v_esperados, v_fallos;
    END IF;

    RAISE NOTICE 'Caso cantidad invalida: OK';
END;
$$;

-- ===========================================================================
-- Caso: detalle_cotizacion con precio negativo o NaN
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_fallos        integer := 0;
BEGIN
    SELECT id_cotizacion INTO v_id_cotizacion FROM test_vars;

    BEGIN
        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES (v_id_cotizacion, 'material', 'x', 'u', 1.000, -10.00);
        RAISE EXCEPTION 'Caso precio negativo: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            v_fallos := v_fallos + 1;
    END;

    BEGIN
        INSERT INTO tallerclaro.detalle_cotizacion (
            id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
        )
        VALUES (v_id_cotizacion, 'material', 'x', 'u', 1.000, 'NaN'::numeric);
        RAISE EXCEPTION 'Caso precio NaN: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            v_fallos := v_fallos + 1;
    END;

    IF v_fallos <> 2 THEN
        RAISE EXCEPTION 'Caso precio invalido: se esperaban 2 rechazos, se obtuvieron %', v_fallos;
    END IF;

    RAISE NOTICE 'Caso precio invalido: OK';
END;
$$;

-- ===========================================================================
-- Caso: importe de detalle con redondeo 0.333 * 10.00 = 3.33
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_importe       numeric(14,2);
BEGIN
    SELECT id_cotizacion INTO v_id_cotizacion FROM test_vars;

    INSERT INTO tallerclaro.detalle_cotizacion (
        id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
    )
    VALUES (v_id_cotizacion, 'other', 'Concepto fraccionario', 'u', 0.333, 10.00)
    RETURNING importe INTO v_importe;

    IF v_importe <> 3.33 THEN
        RAISE EXCEPTION 'Caso redondeo: importe esperado 3.33, obtenido %', v_importe;
    END IF;

    RAISE NOTICE 'Caso redondeo: OK';
END;
$$;

-- ===========================================================================
-- Caso: intentar escribir la columna generada importe
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_id_detalle    bigint;
BEGIN
    SELECT id_cotizacion INTO v_id_cotizacion FROM test_vars;

    INSERT INTO tallerclaro.detalle_cotizacion (
        id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
    )
    VALUES (v_id_cotizacion, 'other', 'Generado', 'u', 1.000, 1.00)
    RETURNING id_detalle INTO v_id_detalle;

    BEGIN
        UPDATE tallerclaro.detalle_cotizacion
        SET importe = 999.99
        WHERE id_detalle = v_id_detalle;
        RAISE EXCEPTION 'Caso columna generada: no fue rechazado';
    EXCEPTION
        WHEN SQLSTATE '428C9' THEN
            RAISE NOTICE 'Caso columna generada: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: cotizacion con cliente inexistente
-- ===========================================================================
DO $$
DECLARE
    v_id_carpintero bigint;
BEGIN
    SELECT id_carpintero INTO v_id_carpintero FROM test_vars;

    BEGIN
        INSERT INTO tallerclaro.cotizacion (
            id_cliente, id_carpintero, solicitud, descripcion,
            monto_total, estado, moneda
        )
        VALUES (-1, v_id_carpintero, 'x', 'y', 100.00, 'approved', 'USD');
        RAISE EXCEPTION 'Caso cliente inexistente: no fue rechazado';
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Caso cliente inexistente: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: pedido con carpintero distinto al de la cotizacion (FK compuesta)
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion     bigint;
    v_id_carpintero_2   bigint;
    v_codigo            text;
BEGIN
    SELECT id_cotizacion, id_carpintero_2
      INTO v_id_cotizacion, v_id_carpintero_2
      FROM test_vars;

    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');

    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero_2, v_codigo,
            350.00, 175.00, 'USD', 'pending'
        );
        RAISE EXCEPTION 'Caso carpintero distinto: no fue rechazado';
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Caso carpintero distinto: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: dos pedidos para la misma cotizacion
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_id_carpintero bigint;
    v_codigo        text;
BEGIN
    SELECT id_cotizacion, id_carpintero
      INTO v_id_cotizacion, v_id_carpintero
      FROM test_vars;

    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');

    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero, v_codigo,
            350.00, 175.00, 'USD', 'pending'
        );
        RAISE EXCEPTION 'Caso dos pedidos misma cotizacion: no fue rechazado';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'Caso dos pedidos misma cotizacion: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: codigo de pedido duplicado
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_id_carpintero bigint;
    v_codigo        text;
BEGIN
    SELECT id_cotizacion, id_carpintero, codigo_pedido
      INTO v_id_cotizacion, v_id_carpintero, v_codigo
      FROM test_vars;

    -- Para poder violar solo la UQ del codigo usamos otra cotizacion aprobada
    INSERT INTO tallerclaro.cotizacion (
        id_cliente, id_carpintero, solicitud, descripcion,
        monto_total, estado, moneda
    )
    SELECT id_cliente, id_carpintero, 'otra', 'otra', 100.00, 'approved', 'USD'
    FROM test_vars;

    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        SELECT id_cotizacion, id_carpintero, v_codigo, 100.00, 50.00, 'USD', 'pending'
        FROM tallerclaro.cotizacion
        WHERE solicitud = 'otra';

        RAISE EXCEPTION 'Caso codigo duplicado: no fue rechazado';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'Caso codigo duplicado: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: anticipo superior al total o negativo
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_id_carpintero bigint;
    v_codigo        text;
BEGIN
    SELECT id_cotizacion, id_carpintero
      INTO v_id_cotizacion, v_id_carpintero
      FROM test_vars;

    -- anticipo superior al total
    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');
    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero, v_codigo,
            350.00, 400.00, 'USD', 'pending'
        );
        RAISE EXCEPTION 'Caso anticipo superior: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Caso anticipo superior: OK';
    END;

    -- anticipo negativo
    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');
    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero, v_codigo,
            350.00, -10.00, 'USD', 'pending'
        );
        RAISE EXCEPTION 'Caso anticipo negativo: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Caso anticipo negativo: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: estado desconocido en pedido
-- ===========================================================================
DO $$
DECLARE
    v_id_cotizacion bigint;
    v_id_carpintero bigint;
    v_codigo        text;
BEGIN
    SELECT id_cotizacion, id_carpintero
      INTO v_id_cotizacion, v_id_carpintero
      FROM test_vars;

    v_codigo := 'TC-' || replace(gen_random_uuid()::text, '-', '');

    BEGIN
        INSERT INTO tallerclaro.pedido (
            id_cotizacion, id_carpintero, codigo, monto_total,
            monto_anticipo, moneda, estado
        )
        VALUES (
            v_id_cotizacion, v_id_carpintero, v_codigo,
            350.00, 175.00, 'USD', 'quote_sent'
        );
        RAISE EXCEPTION 'Caso estado desconocido: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Caso estado desconocido: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: pago pending sin fecha ni IDs PayPal
-- ===========================================================================
DO $$
DECLARE
    v_id_pedido bigint;
    v_id_pago   bigint;
BEGIN
    SELECT id_pedido INTO v_id_pedido FROM test_vars;

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 175.00, 'USD', 'pending',
        NULL, NULL, NULL
    )
    RETURNING id_pago INTO v_id_pago;

    RAISE NOTICE 'Caso pago pending sin datos: OK (id_pago=%)', v_id_pago;
END;
$$;

-- ===========================================================================
-- Caso: pago completed sin captura o fecha
-- ===========================================================================
DO $$
DECLARE
    v_id_pedido bigint;
BEGIN
    SELECT id_pedido INTO v_id_pedido FROM test_vars;

    BEGIN
        INSERT INTO tallerclaro.pago (
            id_pedido, tipo, monto, moneda, estado,
            paypal_order_id, paypal_capture_id, fecha_pago
        )
        VALUES (
            v_id_pedido, 'deposit', 175.00, 'USD', 'completed',
            'ORDER_001', NULL, now()
        );
        RAISE EXCEPTION 'Caso completed sin capture: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Caso completed sin capture: OK';
    END;

    BEGIN
        INSERT INTO tallerclaro.pago (
            id_pedido, tipo, monto, moneda, estado,
            paypal_order_id, paypal_capture_id, fecha_pago
        )
        VALUES (
            v_id_pedido, 'deposit', 175.00, 'USD', 'completed',
            'ORDER_002', 'CAPTURE_002', NULL
        );
        RAISE EXCEPTION 'Caso completed sin fecha_pago: no fue rechazado';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE 'Caso completed sin fecha_pago: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: paypal_order_id y paypal_capture_id duplicados
-- ===========================================================================
DO $$
DECLARE
    v_id_pedido bigint;
BEGIN
    SELECT id_pedido INTO v_id_pedido FROM test_vars;

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 10.00, 'USD', 'completed',
        'ORDER_DUP', 'CAPTURE_DUP', now()
    );

    BEGIN
        INSERT INTO tallerclaro.pago (
            id_pedido, tipo, monto, moneda, estado,
            paypal_order_id, paypal_capture_id, fecha_pago
        )
        VALUES (
            v_id_pedido, 'balance', 10.00, 'USD', 'completed',
            'ORDER_DUP', 'CAPTURE_OTHER', now()
        );
        RAISE EXCEPTION 'Caso order_id duplicado: no fue rechazado';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'Caso order_id duplicado: OK';
    END;

    BEGIN
        INSERT INTO tallerclaro.pago (
            id_pedido, tipo, monto, moneda, estado,
            paypal_order_id, paypal_capture_id, fecha_pago
        )
        VALUES (
            v_id_pedido, 'balance', 10.00, 'USD', 'completed',
            'ORDER_OTHER', 'CAPTURE_DUP', now()
        );
        RAISE EXCEPTION 'Caso capture_id duplicado: no fue rechazado';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'Caso capture_id duplicado: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: varios intentos con IDs PayPal NULL y reintento tras failed
-- ===========================================================================
DO $$
DECLARE
    v_id_pedido bigint;
BEGIN
    SELECT id_pedido INTO v_id_pedido FROM test_vars;

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 50.00, 'USD', 'failed',
        NULL, NULL, NULL
    );

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 50.00, 'USD', 'failed',
        NULL, NULL, NULL
    );

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 50.00, 'USD', 'pending',
        NULL, NULL, NULL
    );

    RAISE NOTICE 'Caso reintentos con IDs NULL: OK';
END;
$$;

-- ===========================================================================
-- Caso: borrar cliente con cotizaciones o pedido con pagos
-- ===========================================================================
DO $$
DECLARE
    v_id_cliente bigint;
    v_id_pedido  bigint;
BEGIN
    SELECT id_cliente, id_pedido
      INTO v_id_cliente, v_id_pedido
      FROM test_vars;

    BEGIN
        DELETE FROM tallerclaro.cliente WHERE id_cliente = v_id_cliente;
        RAISE EXCEPTION 'Caso borrar cliente: no fue rechazado';
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Caso borrar cliente: OK';
    END;

    BEGIN
        DELETE FROM tallerclaro.pedido WHERE id_pedido = v_id_pedido;
        RAISE EXCEPTION 'Caso borrar pedido: no fue rechazado';
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE 'Caso borrar pedido: OK';
    END;
END;
$$;

-- ===========================================================================
-- Caso: actualizar ultima_actualizacion en cliente, cotizacion, pedido y pago
-- ===========================================================================
DO $$
DECLARE
    v_id_cliente        bigint;
    v_id_cotizacion     bigint;
    v_id_pedido         bigint;
    v_id_pago           bigint;
    v_antes             timestamptz;
    v_despues           timestamptz;
BEGIN
    SELECT id_cliente, id_cotizacion, id_pedido
      INTO v_id_cliente, v_id_cotizacion, v_id_pedido
      FROM test_vars;

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'balance', 10.00, 'USD', 'pending',
        NULL, NULL, NULL
    )
    RETURNING id_pago INTO v_id_pago;

    SELECT ultima_actualizacion INTO v_antes FROM tallerclaro.cliente WHERE id_cliente = v_id_cliente;
    UPDATE tallerclaro.cliente SET nombre = nombre WHERE id_cliente = v_id_cliente;
    SELECT ultima_actualizacion INTO v_despues FROM tallerclaro.cliente WHERE id_cliente = v_id_cliente;
    IF v_despues <= v_antes THEN
        RAISE EXCEPTION 'Caso timestamp cliente: no se actualizo';
    END IF;

    SELECT ultima_actualizacion INTO v_antes FROM tallerclaro.cotizacion WHERE id_cotizacion = v_id_cotizacion;
    UPDATE tallerclaro.cotizacion SET descripcion = descripcion WHERE id_cotizacion = v_id_cotizacion;
    SELECT ultima_actualizacion INTO v_despues FROM tallerclaro.cotizacion WHERE id_cotizacion = v_id_cotizacion;
    IF v_despues <= v_antes THEN
        RAISE EXCEPTION 'Caso timestamp cotizacion: no se actualizo';
    END IF;

    SELECT ultima_actualizacion INTO v_antes FROM tallerclaro.pedido WHERE id_pedido = v_id_pedido;
    UPDATE tallerclaro.pedido SET estado = estado WHERE id_pedido = v_id_pedido;
    SELECT ultima_actualizacion INTO v_despues FROM tallerclaro.pedido WHERE id_pedido = v_id_pedido;
    IF v_despues <= v_antes THEN
        RAISE EXCEPTION 'Caso timestamp pedido: no se actualizo';
    END IF;

    SELECT ultima_actualizacion INTO v_antes FROM tallerclaro.pago WHERE id_pago = v_id_pago;
    UPDATE tallerclaro.pago SET estado = estado WHERE id_pago = v_id_pago;
    SELECT ultima_actualizacion INTO v_despues FROM tallerclaro.pago WHERE id_pago = v_id_pago;
    IF v_despues <= v_antes THEN
        RAISE EXCEPTION 'Caso timestamp pago: no se actualizo';
    END IF;

    RAISE NOTICE 'Caso timestamps: OK';
END;
$$;

-- ===========================================================================
-- Caso: reaplicar schema.sql debe fallar (simulado con CREATE SCHEMA)
-- ===========================================================================
DO $$
BEGIN
    BEGIN
        CREATE SCHEMA tallerclaro;
        RAISE EXCEPTION 'Caso reaplicar esquema: no fue rechazado';
    EXCEPTION
        WHEN duplicate_schema THEN
            RAISE NOTICE 'Caso reaplicar esquema: OK';
    END;
END;
$$;

ROLLBACK;
