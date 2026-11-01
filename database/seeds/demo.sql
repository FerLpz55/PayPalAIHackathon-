-- TallerClaro - Datos de demostracion ficticios
-- Ejecutar despues de aplicar database/schema.sql.
-- Estos datos son ilustrativos; no contienen informacion personal real.

BEGIN;

DO $$
DECLARE
    v_id_carpintero_1 bigint;
    v_id_carpintero_2 bigint;
    v_id_cliente      bigint;
    v_id_cotizacion   bigint;
    v_id_pedido       bigint;
    v_codigo_pedido   text;
BEGIN
    INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo, telefono)
    VALUES ('Jose Martinez', 'Carpinteria Martinez', 'jose@martinez.example', '5512345678')
    RETURNING id_carpintero INTO v_id_carpintero_1;

    INSERT INTO tallerclaro.carpintero (nombre, nombre_taller, correo, telefono)
    VALUES ('Ana Lopez', 'Madera y Diseno Lopez', 'ana@lopez.example', '5587654321')
    RETURNING id_carpintero INTO v_id_carpintero_2;

    INSERT INTO tallerclaro.cliente (nombre, correo, telefono)
    VALUES ('Carlos Ficticio', 'carlos@example.com', '5555555555')
    RETURNING id_cliente INTO v_id_cliente;

    INSERT INTO tallerclaro.cotizacion (
        id_cliente, id_carpintero, solicitud, descripcion,
        monto_total, estado, moneda
    )
    VALUES (
        v_id_cliente, v_id_carpintero_1,
        'Mesa de comedor de madera solida para 6 personas',
        'Mesa con patas torneadas y acabado barnizado. Incluye material y mano de obra.',
        350.00, 'approved', 'MXN'
    )
    RETURNING id_cotizacion INTO v_id_cotizacion;

    INSERT INTO tallerclaro.detalle_cotizacion (
        id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario
    )
    VALUES
        (v_id_cotizacion, 'material', 'Madera de encino', 'pieza', 2.000, 100.00),
        (v_id_cotizacion, 'labor', 'Carpinteria y ensamble', 'servicio', 1.000, 150.00);

    v_codigo_pedido := 'TC-' || replace(gen_random_uuid()::text, '-', '');

    INSERT INTO tallerclaro.pedido (
        id_cotizacion, id_carpintero, codigo, monto_total,
        monto_anticipo, moneda, estado, fecha_entrega_estimada
    )
    VALUES (
        v_id_cotizacion, v_id_carpintero_1, v_codigo_pedido,
        350.00, 175.00, 'MXN', 'pending', CURRENT_DATE + 14
    )
    RETURNING id_pedido INTO v_id_pedido;

    INSERT INTO tallerclaro.pago (
        id_pedido, tipo, monto, moneda, estado,
        paypal_order_id, paypal_capture_id, fecha_pago
    )
    VALUES (
        v_id_pedido, 'deposit', 175.00, 'MXN', 'pending',
        NULL, NULL, NULL
    );

    RAISE NOTICE 'Demo creado: cotizacion=%, pedido=%', v_id_cotizacion, v_id_pedido;
END;
$$;

COMMIT;
