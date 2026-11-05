"""Pruebas del resumen financiero del taller."""

from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal

from tallerclaro.domain.accounting import WorkshopFinancialSummary, summarize_workshop_finances
from tallerclaro.domain.entities import (
    CarpenterId,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    QuoteId,
)


def _order(order_id: int, total: str, status: str = "in_progress") -> Order:
    total_money = Money(total)
    return Order(
        id=OrderId(order_id),
        quote_id=QuoteId(order_id),
        carpenter_id=CarpenterId(1),
        code=f"TC-{order_id}",
        total=total_money,
        deposit_amount=Money(total_money.amount / 2),
        currency="USD",
        status=status,
        created_at=None,
        updated_at=None,
    )


def _payment(payment_id: int, order_id: int, kind: str, amount: str, status: str = "completed") -> Payment:
    return Payment(
        id=PaymentId(payment_id),
        order_id=OrderId(order_id),
        type=kind,
        amount=Money(amount),
        currency="USD",
        status=status,
        paypal_order_id=f"P-{payment_id}",
        paypal_capture_id=f"C-{payment_id}" if status == "completed" else None,
        created_at=None,
        updated_at=None,
        paid_at=datetime.now(timezone.utc) if status == "completed" else None,
    )


def test_summary_counts_only_completed_payments():
    orders = [_order(1, "1200"), _order(2, "1000", "delivered"), _order(3, "450", "pending")]
    payments = {
        OrderId(1): [_payment(1, 1, "deposit", "600")],
        OrderId(2): [_payment(2, 2, "deposit", "500"), _payment(3, 2, "balance", "500")],
        OrderId(3): [_payment(4, 3, "deposit", "225", status="pending")],
    }

    summary = summarize_workshop_finances(orders, payments)

    assert summary.currency == "USD"
    assert summary.orders_count == 3
    assert summary.delivered_orders_count == 1
    assert summary.active_orders_count == 2
    assert summary.total_contracted == Money("2650")
    assert summary.collected_total == Money("1600")
    assert summary.collected_deposits == Money("1100")
    assert summary.collected_balances == Money("500")
    assert summary.pending_to_collect == Money("1050")
    assert summary.orders_awaiting_deposit == 1
    assert summary.orders_with_balance_due == 1


def test_summary_average_is_rounded_to_cents():
    orders = [_order(1, "100"), _order(2, "100"), _order(3, "100.01")]
    summary = summarize_workshop_finances(orders, {})
    assert summary.average_order_value.amount == Decimal("100.00")
    assert summary.pending_to_collect == Money("300.01")


def test_summary_of_empty_workshop_is_zero():
    summary = summarize_workshop_finances([], {})
    assert summary.orders_count == 0
    assert summary.collected_total == Money.zero()
    assert summary.average_order_value == Money.zero()


def test_summary_has_no_personal_data_fields():
    names = {field.name for field in fields(WorkshopFinancialSummary)}
    for forbidden in ("customer", "name", "email", "phone"):
        assert not any(forbidden in name for name in names)
