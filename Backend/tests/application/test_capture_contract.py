"""Contrato de captura: reserva, liberación y validación estricta."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tallerclaro.application.dtos import CapturedPayment, PaymentIntent
from tallerclaro.application.exceptions import ConflictError, DomainError
from tallerclaro.application.use_cases import CapturePayment, CreateOrderPayment
from tallerclaro.domain.entities import (
    ORDER_STATUS_PENDING,
    CarpenterId,
    Money,
    Order,
    QuoteId,
)
from tests.fakes import FakePaymentProcessor, FakeUnitOfWork


def _order(uow: FakeUnitOfWork) -> Order:
    with uow:
        result = uow.orders.save(
            Order(
                id=None,
                quote_id=QuoteId(1),
                carpenter_id=CarpenterId(1),
                code="TC-1",
                total=Money("200.00"),
                deposit_amount=Money("100.00"),
                currency="USD",
                status=ORDER_STATUS_PENDING,
                created_at=None,
                updated_at=None,
            )
        )
        uow.commit()
        return result


class _UncertainProcessor:
    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        raise AssertionError("not used")

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        raise DomainError(code="PAYMENT_PROVIDER_ERROR", message="PayPal transport unavailable")


class _FixedCaptureProcessor(FakePaymentProcessor):
    def __init__(self, amount: Decimal, status: str = "completed") -> None:
        super().__init__()
        self._fixed_amount = amount
        self._fixed_status = status

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        return CapturedPayment(
            payment_id=0,
            status=self._fixed_status,
            paypal_order_id=paypal_order_id,
            paypal_capture_id="CAP-1",
            amount=self._fixed_amount,
            currency="USD",
            paid_at="2026-11-02T20:00:00+00:00",
        )


def test_uncertain_capture_keeps_reservation_and_blocks_other_payments():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    deposit = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    balance = CreateOrderPayment(uow, processor).execute(order.id, "balance")

    with pytest.raises(DomainError) as raised:
        CapturePayment(uow, _UncertainProcessor()).execute(deposit.payment_id)
    assert raised.value.code == "PAYMENT_PROVIDER_ERROR"

    with uow:
        assert uow.capture_reservations._captures.get(order.id) == deposit.payment_id

    with pytest.raises(ConflictError, match="Another capture is in progress"):
        CapturePayment(uow, processor).execute(balance.payment_id)
    with uow:
        assert uow.capture_reservations._captures.get(order.id) == deposit.payment_id

    captured = CapturePayment(uow, processor).execute(deposit.payment_id)
    assert captured.status == "completed"
    with uow:
        assert uow.capture_reservations._captures.get(order.id) is None


@pytest.mark.parametrize(
    "captured_amount",
    [Decimal("NaN"), Decimal("Infinity"), Decimal("-100.00"), Decimal("100.000")],
)
def test_capture_rejects_invalid_amounts_and_keeps_reservation(captured_amount):
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    with pytest.raises(ConflictError):
        CapturePayment(uow, _FixedCaptureProcessor(captured_amount)).execute(intent.payment_id)

    with uow:
        assert uow.capture_reservations._captures.get(order.id) == intent.payment_id


def test_capture_rejects_non_completed_status_before_persisting():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    with pytest.raises(ConflictError, match="not completed"):
        CapturePayment(
            uow, _FixedCaptureProcessor(Decimal("100.00"), status="pending")
        ).execute(intent.payment_id)

    with uow:
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"
    with uow:
        assert uow.capture_reservations._captures.get(order.id) == intent.payment_id


def test_create_payment_rejects_duplicate_deposit_intent_after_capture():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    first = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(first.payment_id)

    with pytest.raises(ConflictError, match="Deposit already paid"):
        CreateOrderPayment(uow, processor).execute(order.id, "deposit")


def test_create_payment_rejects_balance_after_full_payment():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    first = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(first.payment_id)
    balance = CreateOrderPayment(uow, processor).execute(order.id, "balance")
    CapturePayment(uow, processor).execute(balance.payment_id)

    with pytest.raises(ConflictError, match="positive"):
        CreateOrderPayment(uow, processor).execute(order.id, "balance")
