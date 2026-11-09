"""Repositorios PostgreSQL."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone

import psycopg

from tallerclaro.application.interfaces import (
    CarpenterRepository,
    CustomerRepository,
    OrderRepository,
    PaymentRepository,
    QuoteRepository,
)
from tallerclaro.domain.entities import (
    Carpenter,
    CarpenterId,
    Customer,
    CustomerId,
    LineItemType,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    PaymentStatus,
    PaymentType,
    Quote,
    QuoteId,
    QuoteLineItem,
    QuoteLineItemId,
)

_ORDER_SELECT_COLUMNS = (
    "id_pedido, id_cotizacion, id_carpintero, codigo, monto_total, "
    "monto_anticipo, moneda, estado, fecha_creacion, ultima_actualizacion, "
    "fecha_entrega_estimada"
)

_PAYMENT_SELECT_COLUMNS = (
    "id_pago, id_pedido, tipo, monto, moneda, estado, "
    "paypal_order_id, paypal_capture_id, fecha_creacion, "
    "ultima_actualizacion, fecha_pago, clave_idempotencia, "
    "huella_solicitud, paypal_approval_url"
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresCustomerRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def save(self, customer: Customer) -> Customer:
        if customer.id is None:
            row = self._conn.execute(
                """
                INSERT INTO tallerclaro.cliente (nombre, correo, telefono)
                VALUES (%s, %s, %s)
                RETURNING id_cliente, fecha_creacion, ultima_actualizacion
                """,
                (customer.name, customer.email, customer.phone),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                UPDATE tallerclaro.cliente
                SET nombre = %s, correo = %s, telefono = %s
                WHERE id_cliente = %s
                RETURNING id_cliente, fecha_creacion, ultima_actualizacion
                """,
                (customer.name, customer.email, customer.phone, customer.id),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save customer")

        raw_id, created_at, updated_at = row
        customer.id = CustomerId(raw_id)
        customer.created_at = created_at
        customer.updated_at = updated_at
        return customer

    def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        row = self._conn.execute(
            """
            SELECT id_cliente, nombre, correo, telefono, fecha_creacion, ultima_actualizacion
            FROM tallerclaro.cliente
            WHERE id_cliente = %s
            """,
            (customer_id,),
        ).fetchone()
        if row is None:
            return None

        raw_id, name, email, phone, created_at, updated_at = row
        return Customer(
            id=CustomerId(raw_id),
            name=name,
            email=email,
            phone=phone,
            created_at=created_at,
            updated_at=updated_at,
        )


class PostgresCarpenterRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def get_by_id(self, carpenter_id: CarpenterId) -> Carpenter | None:
        row = self._conn.execute(
            """
            SELECT id_carpintero, nombre, nombre_taller, correo, telefono, fecha_creacion
            FROM tallerclaro.carpintero
            WHERE id_carpintero = %s
            """,
            (carpenter_id,),
        ).fetchone()
        if row is None:
            return None

        raw_id, name, workshop_name, email, phone, created_at = row
        return Carpenter(
            id=CarpenterId(raw_id),
            name=name,
            workshop_name=workshop_name,
            email=email,
            phone=phone,
            created_at=created_at,
        )


class PostgresQuoteRepository:
    """Persistencia de cotizaciones y sus partidas.

    El rol ``tallerclaro_app`` no tiene privilegio ``DELETE`` en PostgreSQL:
    al actualizar las partidas de una cotización se reutilizan los registros
    existentes y los sobrantes se desactivan con ``UPDATE ... SET activo = false``.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def save(self, quote: Quote) -> Quote:
        self._save_quote_header(quote)
        existing_ids = self._list_existing_line_item_ids(quote.id)
        unused_ids = self._sync_line_items(quote.id, quote.line_items, existing_ids)
        self._deactivate_unused_line_items(quote.id, unused_ids)
        return quote

    def get_by_id(self, quote_id: QuoteId) -> Quote | None:
        row = self._conn.execute(
            """
            SELECT id_cotizacion, id_cliente, id_carpintero, solicitud, descripcion,
                   monto_total, estado, moneda, fecha_creacion, ultima_actualizacion,
                   supuestos, informacion_faltante
            FROM tallerclaro.cotizacion
            WHERE id_cotizacion = %s
            """,
            (quote_id,),
        ).fetchone()
        if row is None:
            return None
        quote = self._row_to_quote(row)
        quote.line_items = self._load_line_items(quote_id)
        return quote

    def _save_quote_header(self, quote: Quote) -> None:
        assumptions = list(quote.assumptions or [])
        missing_info = list(quote.missing_info or [])
        total_amount = quote.total.amount if quote.total is not None else None

        if quote.id is None:
            row = self._conn.execute(
                """
                INSERT INTO tallerclaro.cotizacion
                    (id_cliente, id_carpintero, solicitud, descripcion, monto_total,
                     estado, moneda, supuestos, informacion_faltante)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_cotizacion, fecha_creacion, ultima_actualizacion
                """,
                (
                    quote.customer_id,
                    quote.carpenter_id,
                    quote.request,
                    quote.description,
                    total_amount,
                    quote.status,
                    quote.currency,
                    assumptions,
                    missing_info,
                ),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                UPDATE tallerclaro.cotizacion
                SET id_cliente = %s, id_carpintero = %s, solicitud = %s,
                    descripcion = %s, monto_total = %s, estado = %s, moneda = %s,
                    supuestos = %s, informacion_faltante = %s
                WHERE id_cotizacion = %s
                RETURNING id_cotizacion, fecha_creacion, ultima_actualizacion
                """,
                (
                    quote.customer_id,
                    quote.carpenter_id,
                    quote.request,
                    quote.description,
                    total_amount,
                    quote.status,
                    quote.currency,
                    assumptions,
                    missing_info,
                    quote.id,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save quote")

        raw_id, created_at, updated_at = row
        quote.id = QuoteId(raw_id)
        quote.created_at = created_at
        quote.updated_at = updated_at

    def _list_existing_line_item_ids(self, quote_id: QuoteId) -> list[int]:
        existing_rows = self._conn.execute(
            """
            SELECT id_detalle
            FROM tallerclaro.detalle_cotizacion
            WHERE id_cotizacion = %s
            ORDER BY id_detalle
            """,
            (quote_id,),
        ).fetchall()
        return [row[0] for row in existing_rows]

    def _sync_line_items(
        self,
        quote_id: QuoteId,
        line_items: list[QuoteLineItem],
        existing_ids: list[int],
    ) -> list[int]:
        remaining_ids = list(existing_ids)
        for item in line_items:
            if item.id is not None and item.id in remaining_ids:
                self._update_line_item(quote_id, item.id, item)
                remaining_ids.remove(item.id)
            elif remaining_ids:
                reused_id = remaining_ids.pop(0)
                self._update_line_item(quote_id, reused_id, item)
                self._assign_line_item_id(item, reused_id)
            else:
                self._insert_line_item(quote_id, item)
        return remaining_ids

    def _update_line_item(
        self, quote_id: QuoteId, detail_id: int, item: QuoteLineItem
    ) -> None:
        self._conn.execute(
            """
            UPDATE tallerclaro.detalle_cotizacion
            SET tipo = %s, descripcion = %s, unidad = %s, cantidad = %s,
                precio_unitario = %s, activo = true
            WHERE id_detalle = %s AND id_cotizacion = %s
            """,
            (
                item.type,
                item.description,
                item.unit,
                item.quantity,
                item.unit_price.amount,
                detail_id,
                quote_id,
            ),
        )

    def _insert_line_item(self, quote_id: QuoteId, item: QuoteLineItem) -> None:
        item_row = self._conn.execute(
            """
            INSERT INTO tallerclaro.detalle_cotizacion
                (id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario, activo)
            VALUES (%s, %s, %s, %s, %s, %s, true)
            RETURNING id_detalle
            """,
            (
                quote_id,
                item.type,
                item.description,
                item.unit,
                item.quantity,
                item.unit_price.amount,
            ),
        ).fetchone()
        if item_row is not None:
            self._assign_line_item_id(item, item_row[0])

    def _deactivate_unused_line_items(
        self, quote_id: QuoteId, unused_ids: list[int]
    ) -> None:
        for leftover_id in unused_ids:
            self._conn.execute(
                """
                UPDATE tallerclaro.detalle_cotizacion
                SET activo = false
                WHERE id_detalle = %s AND id_cotizacion = %s
                """,
                (leftover_id, quote_id),
            )

    @staticmethod
    def _assign_line_item_id(item: QuoteLineItem, raw_id: int) -> None:
        line_item_id = QuoteLineItemId(raw_id)
        try:
            item.id = line_item_id
        except (dataclasses.FrozenInstanceError, AttributeError):
            object.__setattr__(item, "id", line_item_id)

    def _row_to_quote(self, row: tuple) -> Quote:
        (
            raw_id,
            customer_id,
            carpenter_id,
            request,
            description,
            total_amount,
            status,
            currency,
            created_at,
            updated_at,
            *extra_columns,
        ) = row
        raw_assumptions = extra_columns[0] if len(extra_columns) > 0 else None
        raw_missing_info = extra_columns[1] if len(extra_columns) > 1 else None
        assumptions = list(raw_assumptions or []) if raw_assumptions is not None else []
        missing_info = list(raw_missing_info or []) if raw_missing_info is not None else []

        return Quote(
            id=QuoteId(raw_id),
            customer_id=CustomerId(customer_id),
            carpenter_id=CarpenterId(carpenter_id),
            request=request,
            description=description,
            total=Money(total_amount) if total_amount is not None else None,
            status=status,
            currency=currency,
            assumptions=assumptions,
            missing_info=missing_info,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _load_line_items(self, quote_id: QuoteId) -> list[QuoteLineItem]:
        rows = self._conn.execute(
            """
            SELECT id_detalle, tipo, descripcion, unidad, cantidad, precio_unitario
            FROM tallerclaro.detalle_cotizacion
            WHERE id_cotizacion = %s AND activo = true
            ORDER BY id_detalle
            """,
            (quote_id,),
        ).fetchall()
        items: list[QuoteLineItem] = []
        for row in rows:
            raw_id, item_type, description, unit, quantity, unit_price = row
            items.append(
                QuoteLineItem(
                    id=QuoteLineItemId(raw_id),
                    type=LineItemType(item_type),
                    description=description,
                    unit=unit,
                    quantity=quantity,
                    unit_price=Money(unit_price),
                )
            )
        return items


class PostgresCaptureReservationRepository:
    """Reserva de captura sobre ``pedido.captura_en_curso``.

    ``reserve`` es un UPDATE condicional atómico; ``release`` solo limpia la
    reserva del pago indicado. Ambos participan de la transacción del UoW.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def reserve(self, order_id: OrderId, payment_id: PaymentId) -> bool:
        row = self._conn.execute(
            "UPDATE tallerclaro.pedido SET captura_en_curso = %s WHERE id_pedido = %s AND (captura_en_curso IS NULL OR captura_en_curso = %s) RETURNING id_pedido",
            (payment_id, order_id, payment_id),
        ).fetchone()
        return row is not None

    def release(self, order_id: OrderId, payment_id: PaymentId) -> None:
        self._conn.execute(
            "UPDATE tallerclaro.pedido SET captura_en_curso = NULL WHERE id_pedido = %s AND captura_en_curso = %s",
            (order_id, payment_id),
        )

    def active_payment_id(self, order_id: OrderId) -> PaymentId | None:
        row = self._conn.execute(
            "SELECT captura_en_curso FROM tallerclaro.pedido WHERE id_pedido = %s",
            (order_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return PaymentId(row[0])


class PostgresOrderRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def save(self, order: Order) -> Order:
        if order.id is None:
            row = self._conn.execute(
                """
                INSERT INTO tallerclaro.pedido
                    (id_cotizacion, id_carpintero, codigo, monto_total, monto_anticipo,
                     moneda, estado, fecha_entrega_estimada)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pedido, fecha_creacion, ultima_actualizacion
                """,
                (
                    order.quote_id,
                    order.carpenter_id,
                    order.code,
                    order.total.amount,
                    order.deposit_amount.amount,
                    order.currency,
                    order.status,
                    order.estimated_delivery_date,
                ),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                UPDATE tallerclaro.pedido
                SET id_cotizacion = %s, id_carpintero = %s, codigo = %s,
                    monto_total = %s, monto_anticipo = %s, moneda = %s,
                    estado = %s, fecha_entrega_estimada = %s
                WHERE id_pedido = %s
                RETURNING id_pedido, fecha_creacion, ultima_actualizacion
                """,
                (
                    order.quote_id,
                    order.carpenter_id,
                    order.code,
                    order.total.amount,
                    order.deposit_amount.amount,
                    order.currency,
                    order.status,
                    order.estimated_delivery_date,
                    order.id,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save order")

        raw_id, created_at, updated_at = row
        order.id = OrderId(raw_id)
        order.created_at = created_at
        order.updated_at = updated_at
        return order

    def get_by_id(self, order_id: OrderId) -> Order | None:
        row = self._conn.execute(
            f"""
            SELECT {_ORDER_SELECT_COLUMNS}
            FROM tallerclaro.pedido
            WHERE id_pedido = %s
            """,
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_order(row)

    def get_by_quote_id(self, quote_id: QuoteId) -> Order | None:
        row = self._conn.execute(
            f"""
            SELECT {_ORDER_SELECT_COLUMNS}
            FROM tallerclaro.pedido
            WHERE id_cotizacion = %s
            """,
            (quote_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_order(row)

    def list_by_carpenter(
        self, carpenter_id: CarpenterId, limit: int, offset: int
    ) -> list[Order]:
        rows = self._conn.execute(
            f"""
            SELECT {_ORDER_SELECT_COLUMNS}
            FROM tallerclaro.pedido
            WHERE id_carpintero = %s AND estado <> 'deleted'
            ORDER BY fecha_creacion DESC
            LIMIT %s OFFSET %s
            """,
            (carpenter_id, limit, offset),
        ).fetchall()
        return [self._row_to_order(row) for row in rows]

    def count_by_carpenter(self, carpenter_id: CarpenterId) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*)
            FROM tallerclaro.pedido
            WHERE id_carpintero = %s AND estado <> 'deleted'
            """,
            (carpenter_id,),
        ).fetchone()
        return row[0] if row is not None else 0

    def _row_to_order(self, row: tuple) -> Order:
        (
            raw_id,
            quote_id,
            carpenter_id,
            code,
            total_amount,
            deposit_amount,
            currency,
            status,
            created_at,
            updated_at,
            estimated_delivery_date,
        ) = row
        return Order(
            id=OrderId(raw_id),
            quote_id=QuoteId(quote_id),
            carpenter_id=CarpenterId(carpenter_id),
            code=code,
            total=Money(total_amount),
            deposit_amount=Money(deposit_amount),
            currency=currency,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            estimated_delivery_date=estimated_delivery_date,
        )


class PostgresPaymentRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def save(self, payment: Payment) -> Payment:
        if payment.id is None:
            row = self._conn.execute(
                """
                INSERT INTO tallerclaro.pago
                    (id_pedido, tipo, monto, moneda, estado,
                     paypal_order_id, paypal_capture_id, fecha_pago,
                     clave_idempotencia, huella_solicitud, paypal_approval_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_pago, fecha_creacion, ultima_actualizacion
                """,
                (
                    payment.order_id,
                    payment.type,
                    payment.amount.amount,
                    payment.currency,
                    payment.status,
                    payment.paypal_order_id,
                    payment.paypal_capture_id,
                    payment.paid_at,
                    payment.idempotency_key,
                    payment.request_fingerprint,
                    payment.approval_url,
                ),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                UPDATE tallerclaro.pago
                SET id_pedido = %s, tipo = %s, monto = %s, moneda = %s, estado = %s,
                    paypal_order_id = %s, paypal_capture_id = %s, fecha_pago = %s,
                    clave_idempotencia = %s, huella_solicitud = %s,
                    paypal_approval_url = %s
                WHERE id_pago = %s
                RETURNING id_pago, fecha_creacion, ultima_actualizacion
                """,
                (
                    payment.order_id,
                    payment.type,
                    payment.amount.amount,
                    payment.currency,
                    payment.status,
                    payment.paypal_order_id,
                    payment.paypal_capture_id,
                    payment.paid_at,
                    payment.idempotency_key,
                    payment.request_fingerprint,
                    payment.approval_url,
                    payment.id,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save payment")

        raw_id, created_at, updated_at = row
        payment.id = PaymentId(raw_id)
        payment.created_at = created_at
        payment.updated_at = updated_at
        return payment

    def get_by_id(self, payment_id: PaymentId) -> Payment | None:
        row = self._conn.execute(
            f"""
            SELECT {_PAYMENT_SELECT_COLUMNS}
            FROM tallerclaro.pago
            WHERE id_pago = %s
            """,
            (payment_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_payment(row)

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        rows = self._conn.execute(
            f"""
            SELECT {_PAYMENT_SELECT_COLUMNS}
            FROM tallerclaro.pago
            WHERE id_pedido = %s
            ORDER BY fecha_creacion
            """,
            (order_id,),
        ).fetchall()
        return [self._row_to_payment(row) for row in rows]

    def get_pending_by_order_and_type(
        self, order_id: OrderId, payment_type: PaymentType
    ) -> Payment | None:
        row = self._conn.execute(
            f"""
            SELECT {_PAYMENT_SELECT_COLUMNS}
            FROM tallerclaro.pago
            WHERE id_pedido = %s AND tipo = %s AND estado = 'pending'
            ORDER BY fecha_creacion DESC
            LIMIT 1
            """,
            (order_id, payment_type),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_payment(row)

    def _row_to_payment(self, row: tuple) -> Payment:
        (
            raw_id,
            order_id,
            payment_type,
            amount,
            currency,
            status,
            paypal_order_id,
            paypal_capture_id,
            created_at,
            updated_at,
            paid_at,
            idempotency_key,
            request_fingerprint,
            approval_url,
        ) = row
        return Payment(
            id=PaymentId(raw_id),
            order_id=OrderId(order_id),
            type=PaymentType(payment_type),
            amount=Money(amount),
            currency=currency,
            status=PaymentStatus(status),
            paypal_order_id=paypal_order_id,
            paypal_capture_id=paypal_capture_id,
            created_at=created_at,
            updated_at=updated_at,
            paid_at=paid_at,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            approval_url=approval_url,
        )
