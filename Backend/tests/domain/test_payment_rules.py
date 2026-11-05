"""Reglas monetarias del dominio para pedidos y pagos."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from tallerclaro.domain.entities import (
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_STATUS_PENDING,
    PAYMENT_TYPE_BALANCE,
    PAYMENT_TYPE_DEPOSIT,
    Order,
    OrderId,
    Payment,
    PaymentId,
    QuoteId,
)
from tallerclaro.domain.exceptions import ConflictError, ValidationDomainError
from tallerclaro.domain.value_objects import Money


def _order(total: str = "200.00", deposit: str = "100.00") -> Order:
    return Order(
        id=OrderId(1),
        quote_id=QuoteId(1),
        carpenter_id=1,
        code="TC-1",
        total=Money(total),
        deposit_amount=Money(deposit),
        currency="USD",
        status=ORDER_STATUS_PENDING,
        created_at=None,
        updated_at=None,
    )


def _payment(
    amount: str,
    payment_type: str = PAYMENT_TYPE_DEPOSIT,
    status: str = PAYMENT_STATUS_COMPLETED,
    payment_id: int = 1,
    currency: str = "USD",
) -> Payment:
    return Payment(
        id=PaymentId(payment_id),
        order_id=OrderId(1),
        type=payment_type,
        amount=Money(amount),
        currency=currency,
        status=status,
        paypal_order_id="PP-1",
        paypal_capture_id="CAP-1" if status == PAYMENT_STATUS_COMPLETED else None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        paid_at=datetime.now(timezone.utc) if status == PAYMENT_STATUS_COMPLETED else None,
    )


def test_requested_deposit_and_balance_on_fresh_order():
    order = _order()

    assert order.requested_payment_amount(PAYMENT_TYPE_DEPOSIT, []) == Money("100.00")
    assert order.requested_payment_amount(PAYMENT_TYPE_BALANCE, []) == Money("200.00")


def test_requested_balance_after_completed_deposit():
    order = _order()
    paid_deposit = _payment("100.00")

    assert order.requested_payment_amount(PAYMENT_TYPE_BALANCE, [paid_deposit]) == Money("100.00")
    assert order.calculate_paid_amount([paid_deposit]) == Money("100.00")
    assert order.calculate_remaining_balance([paid_deposit]) == Money("100.00")


def test_requested_amounts_preserve_cent_precision_and_round_half_up():
    order = _order(total="199.99", deposit="99.995")

    assert order.deposit_amount == Money("100.00")
    assert order.requested_payment_amount(PAYMENT_TYPE_DEPOSIT, []) == Money("100.00")
    assert order.calculate_remaining_balance([]) == Money("199.99")
    assert order.requested_payment_amount(PAYMENT_TYPE_BALANCE, []) == Money("199.99")


def test_requested_balance_rejects_exhausted_balance():
    order = _order(total="100.00", deposit="50.00")
    paid = _payment("100.00", payment_type=PAYMENT_TYPE_BALANCE)

    with pytest.raises(ConflictError, match="positive"):
        order.requested_payment_amount(PAYMENT_TYPE_BALANCE, [paid])


def test_requested_deposit_rejects_overpayment_beyond_remaining():
    order = _order(total="150.00", deposit="100.00")
    partial = _payment("120.00", payment_type=PAYMENT_TYPE_BALANCE)

    with pytest.raises(ConflictError, match="exceeds remaining balance"):
        order.requested_payment_amount(PAYMENT_TYPE_DEPOSIT, [partial])


def test_requested_deposit_rejects_already_completed_deposit():
    order = _order()
    paid_deposit = _payment("100.00")

    with pytest.raises(ConflictError, match="Deposit already paid"):
        order.requested_payment_amount(PAYMENT_TYPE_DEPOSIT, [paid_deposit])


def test_requested_amount_rejects_unknown_payment_type():
    with pytest.raises(ValidationDomainError, match="Invalid payment type"):
        _order().requested_payment_amount("refund", [])


def test_capture_rejects_second_deposit_after_first_completed():
    order = _order()
    completed = _payment("100.00", payment_id=1)
    pending = _payment("100.00", status=PAYMENT_STATUS_PENDING, payment_id=2)

    with pytest.raises(ConflictError, match="Deposit already paid"):
        order.validate_capture(pending, [completed, pending])


def test_capture_rejects_amount_above_remaining_balance():
    order = _order()
    completed = _payment("100.00", payment_id=1)
    stale_balance = _payment(
        "200.00", payment_type=PAYMENT_TYPE_BALANCE, status=PAYMENT_STATUS_PENDING, payment_id=2
    )

    with pytest.raises(ConflictError, match="exceeds remaining balance"):
        order.validate_capture(stale_balance, [completed, stale_balance])


def test_capture_accepts_exact_remaining_balance():
    order = _order()
    completed = _payment("100.00", payment_id=1)
    balance = _payment(
        "100.00", payment_type=PAYMENT_TYPE_BALANCE, status=PAYMENT_STATUS_PENDING, payment_id=2
    )

    order.validate_capture(balance, [completed, balance])


def test_non_usd_order_and_payment_are_rejected():
    with pytest.raises(ValidationDomainError, match="Currency must be USD"):
        Order(
            id=None,
            quote_id=QuoteId(1),
            carpenter_id=1,
            code="TC-1",
            total=Money("200.00"),
            deposit_amount=Money("100.00"),
            currency="MXN",
            status=ORDER_STATUS_PENDING,
            created_at=None,
            updated_at=None,
        )

    with pytest.raises(ValidationDomainError, match="Currency must be USD"):
        Payment(
            id=None,
            order_id=OrderId(1),
            type=PAYMENT_TYPE_DEPOSIT,
            amount=Money("10.00"),
            currency="MXN",
            status=PAYMENT_STATUS_PENDING,
            paypal_order_id=None,
            paypal_capture_id=None,
            created_at=None,
            updated_at=None,
            paid_at=None,
        )


def test_is_fully_paid_uses_completed_payments_only():
    order = _order()
    pending = _payment("200.00", payment_type=PAYMENT_TYPE_BALANCE, status=PAYMENT_STATUS_PENDING)
    completed = _payment("200.00", payment_type=PAYMENT_TYPE_BALANCE)

    assert order.is_fully_paid([pending]) is False
    assert order.is_fully_paid([completed]) is True
    order.update_status(ORDER_STATUS_PAID)
    assert order.status == ORDER_STATUS_PAID


def test_money_quantizes_extra_precision_with_round_half_up():
    assert Money(Decimal("0.005")).amount == Decimal("0.01")
    assert Money(Decimal("0.004")).amount == Decimal("0.00")
    assert Money(Decimal("199.999")).amount == Decimal("200.00")
