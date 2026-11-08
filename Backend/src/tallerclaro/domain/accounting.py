"""Reglas puras para el resumen financiero del taller.

El resumen solo agrega importes y conteos; no contiene datos personales de
clientes, de modo que puede compartirse con el asistente contable sin exponer
nombres ni correos.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_TYPE_BALANCE,
    PAYMENT_TYPE_DEPOSIT,
    Order,
    OrderId,
    Payment,
)
from tallerclaro.domain.value_objects import Money

SUMMARY_CURRENCY = "USD"


@dataclass(frozen=True)
class WorkshopFinancialSummary:
    """Totales del taller calculados a partir de pedidos y pagos verificados."""

    currency: str
    orders_count: int
    active_orders_count: int
    delivered_orders_count: int
    orders_awaiting_deposit: int
    orders_with_balance_due: int
    total_contracted: Money
    collected_total: Money
    collected_deposits: Money
    collected_balances: Money
    pending_to_collect: Money
    average_order_value: Money


def _sum_completed(payments: Iterable[Payment], payment_type: str | None = None) -> Money:
    total = sum(
        (
            payment.amount.amount
            for payment in payments
            if payment.status == PAYMENT_STATUS_COMPLETED
            and (payment_type is None or payment.type == payment_type)
        ),
        Decimal("0"),
    )
    return Money(total)


def summarize_workshop_finances(
    orders: Iterable[Order],
    payments_by_order: Mapping[OrderId, list[Payment]],
) -> WorkshopFinancialSummary:
    """Calcula el resumen financiero con `Decimal` y redondeo a centavos.

    Solo cuentan los pagos en estado ``completed``: un pago pendiente o fallido
    nunca se considera dinero cobrado.
    """

    order_list = list(orders)
    total_contracted = Money.zero()
    collected_total = Money.zero()
    collected_deposits = Money.zero()
    collected_balances = Money.zero()
    pending_to_collect = Money.zero()
    delivered = 0
    awaiting_deposit = 0
    with_balance_due = 0

    for order in order_list:
        payments = payments_by_order.get(order.id, []) if order.id is not None else []
        paid = order.calculate_paid_amount(payments)
        remaining = order.calculate_remaining_balance(payments)

        total_contracted = total_contracted + order.total
        collected_total = collected_total + paid
        collected_deposits = collected_deposits + _sum_completed(payments, PAYMENT_TYPE_DEPOSIT)
        collected_balances = collected_balances + _sum_completed(payments, PAYMENT_TYPE_BALANCE)
        pending_to_collect = pending_to_collect + remaining

        if order.status == ORDER_STATUS_DELIVERED:
            delivered += 1
        if not paid.is_positive():
            awaiting_deposit += 1
        elif remaining.is_positive():
            with_balance_due += 1

    count = len(order_list)
    average = Money(total_contracted.amount / count) if count else Money.zero()

    return WorkshopFinancialSummary(
        currency=SUMMARY_CURRENCY,
        orders_count=count,
        active_orders_count=count - delivered,
        delivered_orders_count=delivered,
        orders_awaiting_deposit=awaiting_deposit,
        orders_with_balance_due=with_balance_due,
        total_contracted=total_contracted,
        collected_total=collected_total,
        collected_deposits=collected_deposits,
        collected_balances=collected_balances,
        pending_to_collect=pending_to_collect,
        average_order_value=average,
    )

