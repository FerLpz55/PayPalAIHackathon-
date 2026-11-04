"""Repositorios PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import dataclasses

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
        customer.id = CustomerId(row[0])
        customer.created_at = row[1]
        customer.updated_at = row[2]
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
        return Customer(
            id=CustomerId(row[0]),
            name=row[1],
            email=row[2],
            phone=row[3],
            created_at=row[4],
            updated_at=row[5],
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
        return Carpenter(
            id=CarpenterId(row[0]),
            name=row[1],
            workshop_name=row[2],
            email=row[3],
            phone=row[4],
            created_at=row[5],
        )


class PostgresQuoteRepository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def save(self, quote: Quote) -> Quote:
        assumptions = list(quote.assumptions or [])
        missing_info = list(quote.missing_info or [])
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
                    quote.total.amount if quote.total is not None else None,
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
                    quote.total.amount if quote.total is not None else None,
                    quote.status,
                    quote.currency,
                    assumptions,
                    missing_info,
                    quote.id,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save quote")
        quote.id = QuoteId(row[0])
        quote.created_at = row[1]
        quote.updated_at = row[2]

        # Persistir partidas sin churn de DELETE
        existing_rows = self._conn.execute(
            """
            SELECT id_detalle
            FROM tallerclaro.detalle_cotizacion
            WHERE id_cotizacion = %s
            ORDER BY id_detalle
            """,
            (quote.id,),
        ).fetchall()
        existing_ids = [row[0] for row in existing_rows]

        for item in quote.line_items:
            if item.id is not None and item.id in existing_ids:
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
                        item.id,
                        quote.id,
                    ),
                )
                existing_ids.remove(item.id)
            elif existing_ids:
                target_id = existing_ids.pop(0)
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
                        target_id,
                        quote.id,
                    ),
                )
                try:
                    item.id = QuoteLineItemId(target_id)
                except (dataclasses.FrozenInstanceError, AttributeError):
                    object.__setattr__(item, "id", QuoteLineItemId(target_id))
            else:
                item_row = self._conn.execute(
                    """
                    INSERT INTO tallerclaro.detalle_cotizacion
                        (id_cotizacion, tipo, descripcion, unidad, cantidad, precio_unitario, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                    RETURNING id_detalle
                    """,
                    (
                        quote.id,
                        item.type,
                        item.description,
                        item.unit,
                        item.quantity,
                        item.unit_price.amount,
                    ),
                ).fetchone()
                if item_row is not None:
                    try:
                        item.id = QuoteLineItemId(item_row[0])
                    except (dataclasses.FrozenInstanceError, AttributeError):
                        object.__setattr__(item, "id", QuoteLineItemId(item_row[0]))

        for leftover_id in existing_ids:
            self._conn.execute(
                """
                UPDATE tallerclaro.detalle_cotizacion
                SET activo = false
                WHERE id_detalle = %s AND id_cotizacion = %s
                """,
                (leftover_id, quote.id),
            )
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

    def get_by_id_with_customer(self, quote_id: QuoteId) -> tuple[Quote, Customer] | None:
        quote = self.get_by_id(quote_id)
        if quote is None:
            return None
        customer = PostgresCustomerRepository(self._conn).get_by_id(quote.customer_id)
        if customer is None:
            return None
        return quote, customer

    def _row_to_quote(self, row: tuple) -> Quote:
        assumptions = list(row[10] or []) if len(row) > 10 and row[10] is not None else []
        missing_info = list(row[11] or []) if len(row) > 11 and row[11] is not None else []
        return Quote(
            id=QuoteId(row[0]),
            customer_id=CustomerId(row[1]),
            carpenter_id=CarpenterId(row[2]),
            request=row[3],
            description=row[4],
            total=Money(row[5]) if row[5] is not None else None,
            status=row[6],
            currency=row[7],
            assumptions=assumptions,
            missing_info=missing_info,
            created_at=row[8],
            updated_at=row[9],
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
        return [
            QuoteLineItem(
                id=QuoteLineItemId(row[0]),
                type=LineItemType(row[1]),
                description=row[2],
                unit=row[3],
                quantity=row[4],
                unit_price=Money(row[5]),
            )
            for row in rows
        ]


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
        order.id = OrderId(row[0])
        order.created_at = row[1]
        order.updated_at = row[2]
        return order

    def get_by_id(self, order_id: OrderId) -> Order | None:
        row = self._conn.execute(
            """
            SELECT id_pedido, id_cotizacion, id_carpintero, codigo, monto_total,
                   monto_anticipo, moneda, estado, fecha_creacion, ultima_actualizacion,
                   fecha_entrega_estimada
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
            """
            SELECT id_pedido, id_cotizacion, id_carpintero, codigo, monto_total,
                   monto_anticipo, moneda, estado, fecha_creacion, ultima_actualizacion,
                   fecha_entrega_estimada
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
            """
            SELECT id_pedido, id_cotizacion, id_carpintero, codigo, monto_total,
                   monto_anticipo, moneda, estado, fecha_creacion, ultima_actualizacion,
                   fecha_entrega_estimada
            FROM tallerclaro.pedido
            WHERE id_carpintero = %s
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
            WHERE id_carpintero = %s
            """,
            (carpenter_id,),
        ).fetchone()
        return row[0] if row is not None else 0

    def _row_to_order(self, row: tuple) -> Order:
        return Order(
            id=OrderId(row[0]),
            quote_id=QuoteId(row[1]),
            carpenter_id=CarpenterId(row[2]),
            code=row[3],
            total=Money(row[4]),
            deposit_amount=Money(row[5]),
            currency=row[6],
            status=row[7],
            created_at=row[8],
            updated_at=row[9],
            estimated_delivery_date=row[10],
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
                     paypal_order_id, paypal_capture_id, fecha_pago)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
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
                ),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                UPDATE tallerclaro.pago
                SET id_pedido = %s, tipo = %s, monto = %s, moneda = %s, estado = %s,
                    paypal_order_id = %s, paypal_capture_id = %s, fecha_pago = %s
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
                    payment.id,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Failed to save payment")
        payment.id = PaymentId(row[0])
        payment.created_at = row[1]
        payment.updated_at = row[2]
        return payment

    def get_by_id(self, payment_id: PaymentId) -> Payment | None:
        row = self._conn.execute(
            """
            SELECT id_pago, id_pedido, tipo, monto, moneda, estado,
                   paypal_order_id, paypal_capture_id, fecha_creacion,
                   ultima_actualizacion, fecha_pago
            FROM tallerclaro.pago
            WHERE id_pago = %s
            """,
            (payment_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_payment(row)

    def get_by_paypal_order_id(self, paypal_order_id: str) -> Payment | None:
        row = self._conn.execute(
            """
            SELECT id_pago, id_pedido, tipo, monto, moneda, estado,
                   paypal_order_id, paypal_capture_id, fecha_creacion,
                   ultima_actualizacion, fecha_pago
            FROM tallerclaro.pago
            WHERE paypal_order_id = %s
            """,
            (paypal_order_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_payment(row)

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        rows = self._conn.execute(
            """
            SELECT id_pago, id_pedido, tipo, monto, moneda, estado,
                   paypal_order_id, paypal_capture_id, fecha_creacion,
                   ultima_actualizacion, fecha_pago
            FROM tallerclaro.pago
            WHERE id_pedido = %s
            ORDER BY fecha_creacion
            """,
            (order_id,),
        ).fetchall()
        return [self._row_to_payment(row) for row in rows]

    def _row_to_payment(self, row: tuple) -> Payment:
        return Payment(
            id=PaymentId(row[0]),
            order_id=OrderId(row[1]),
            type=PaymentType(row[2]),
            amount=Money(row[3]),
            currency=row[4],
            status=PaymentStatus(row[5]),
            paypal_order_id=row[6],
            paypal_capture_id=row[7],
            created_at=row[8],
            updated_at=row[9],
            paid_at=row[10],
        )
