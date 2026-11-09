"""Idempotencia, conciliación y cancelación segura de pagos (Fase D)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tallerclaro.application.dtos import UpdateOrderInput
from tallerclaro.application.exceptions import ConflictError, DomainError
from tallerclaro.application.use_cases import (
    CancelPayment,
    CapturePayment,
    CreateOrderPayment,
    SyncPayment,
    UpdateOrder,
)
from tallerclaro.application.use_cases.payments import PAYMENT_IDEMPOTENCY_WINDOW
from tallerclaro.domain.entities import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_DELETED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    CarpenterId,
    Money,
    Order,
    Payment,
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


def _payments(uow: FakeUnitOfWork, order: Order):
    with uow:
        return uow.payments.list_by_order(order.id)


# --- Idempotencia de creación ---


def test_repeated_create_reuses_the_same_attempt_and_provider_order():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()

    first = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    second = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    assert second.payment_id == first.payment_id
    assert second.paypal_order_id == first.paypal_order_id
    assert second.approval_url == first.approval_url
    # Solo hubo una llamada al proveedor: el reintento es un replay local.
    assert len(processor.create_calls) == 1
    assert processor.create_calls[0]
    assert len(_payments(uow, order)) == 1


def test_pending_attempt_is_persisted_before_calling_the_provider():
    uow = FakeUnitOfWork()
    order = _order(uow)
    seen: dict[str, object] = {}

    class InspectingProcessor(FakePaymentProcessor):
        def create_order(self, amount, currency, request_id=None):
            with uow:
                pending = uow.payments.get_pending_by_order_and_type(order.id, "deposit")
                seen["pending"] = pending
                seen["key"] = request_id
            return super().create_order(amount, currency, request_id)

    intent = CreateOrderPayment(uow, InspectingProcessor()).execute(order.id, "deposit")

    pending = seen["pending"]
    assert pending is not None
    assert pending.id == intent.payment_id
    assert pending.paypal_order_id is None
    assert pending.idempotency_key == seen["key"]
    assert pending.request_fingerprint


def test_retry_after_provider_error_reuses_the_same_idempotency_key():
    uow = FakeUnitOfWork()
    order = _order(uow)
    keys: list[str | None] = []

    class FailsOnceProcessor(FakePaymentProcessor):
        def create_order(self, amount, currency, request_id=None):
            keys.append(request_id)
            if len(keys) == 1:
                raise DomainError(
                    code="PAYMENT_PROVIDER_ERROR",
                    message="PayPal transport unavailable; retry the same payment",
                )
            return super().create_order(amount, currency, request_id)

    processor = FailsOnceProcessor()

    with pytest.raises(DomainError):
        CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    with uow:
        assert uow.payments.get_pending_by_order_and_type(order.id, "deposit") is not None

    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    assert keys[0] is not None
    assert keys[1] == keys[0]
    assert intent.paypal_order_id


def test_changed_amount_while_attempt_is_pending_is_rejected():
    uow = FakeUnitOfWork()
    order = _order(uow)
    CreateOrderPayment(uow, FakePaymentProcessor()).execute(order.id, "deposit")

    with uow:
        changed = uow.orders.get_by_id(order.id)
        changed.deposit_amount = Money("90.00")
        uow.orders.save(changed)
        uow.commit()

    with pytest.raises(ConflictError, match="different payment attempt"):
        CreateOrderPayment(uow, FakePaymentProcessor()).execute(order.id, "deposit")


def test_attempt_outside_the_idempotency_window_must_be_reconciled():
    uow = FakeUnitOfWork()
    order = _order(uow)
    intent = CreateOrderPayment(uow, FakePaymentProcessor()).execute(order.id, "deposit")

    with uow:
        pending = uow.payments.get_by_id(intent.payment_id)
        pending.created_at = (
            datetime.now(timezone.utc)
            - PAYMENT_IDEMPOTENCY_WINDOW
            - timedelta(minutes=1)
        )
        uow.payments.save(pending)
        uow.commit()

    with pytest.raises(ConflictError, match="expired"):
        CreateOrderPayment(uow, FakePaymentProcessor()).execute(order.id, "deposit")


def test_create_is_blocked_while_a_capture_is_uncertain():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    deposit = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    with uow:
        assert uow.capture_reservations.reserve(order.id, deposit.payment_id)
        uow.commit()

    with pytest.raises(ConflictError, match="capture is in progress"):
        CreateOrderPayment(uow, processor).execute(order.id, "balance")


# --- Conciliación ---


def test_sync_does_not_capture_while_the_order_is_only_created():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "pending"
    assert processor.capture_calls == []
    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) is None


def test_sync_persists_an_external_completion_without_capturing_again():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    processor.mark_completed_externally(intent.paypal_order_id)

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "completed"
    assert payment.paypal_capture_id == f"CAPTURE-{intent.paypal_order_id}"
    assert processor.capture_calls == []
    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) is None


def test_sync_captures_only_when_paypal_reports_approved():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    processor.set_order_status(intent.paypal_order_id, "APPROVED")

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "completed"
    assert processor.capture_calls == [intent.paypal_order_id]


def test_sync_cancels_a_voided_provider_order_and_releases_reservation():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    processor.set_order_status(intent.paypal_order_id, "VOIDED")

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "cancelled"
    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) is None


def test_sync_keeps_reservation_when_transport_is_uncertain():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    class UncertainSyncProcessor(FakePaymentProcessor):
        def get_order(self, paypal_order_id):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal transport unavailable; retry the same payment",
            )

    with pytest.raises(DomainError):
        SyncPayment(uow, UncertainSyncProcessor()).execute(intent.payment_id)

    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) == intent.payment_id
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"


# --- Cancelación ---


def test_cancel_pending_payment_is_local_and_allows_a_new_attempt():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    first = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    cancelled = CancelPayment(uow).execute(first.payment_id)
    assert cancelled.status == "cancelled"

    second = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    assert second.payment_id != first.payment_id


def test_cancel_completed_payment_is_rejected():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(intent.payment_id)

    with pytest.raises(ConflictError, match="completed payment"):
        CancelPayment(uow).execute(intent.payment_id)


def test_cancel_refuses_and_keeps_an_uncertain_capture_reservation():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")

    with uow:
        assert uow.capture_reservations.reserve(order.id, intent.payment_id)
        uow.commit()

    with pytest.raises(ConflictError, match="capture is in progress"):
        CancelPayment(uow).execute(intent.payment_id)

    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) == intent.payment_id
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"


# --- Estado financiero y bloqueo del pedido ---


def test_financial_status_derives_from_completed_payments():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()

    assert order.financial_status([]) == "unpaid"

    deposit = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(deposit.payment_id)
    assert order.financial_status(_payments(uow, order)) == "deposit_paid"

    balance = CreateOrderPayment(uow, processor).execute(order.id, "balance")
    CapturePayment(uow, processor).execute(balance.payment_id)
    assert order.financial_status(_payments(uow, order)) == "paid"


def test_order_cannot_be_cancelled_or_deleted_after_a_completed_payment():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(intent.payment_id)

    for target in (ORDER_STATUS_CANCELLED, ORDER_STATUS_DELETED):
        with pytest.raises(ConflictError, match="completed payments"):
            UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=target))


def test_order_cannot_be_cancelled_while_a_capture_is_in_progress():
    uow = FakeUnitOfWork()
    order = _order(uow)
    intent = CreateOrderPayment(uow, FakePaymentProcessor()).execute(order.id, "deposit")

    with uow:
        assert uow.capture_reservations.reserve(order.id, intent.payment_id)
        uow.commit()

    with pytest.raises(ConflictError, match="capture in progress"):
        UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=ORDER_STATUS_CANCELLED))


def test_order_cannot_be_marked_paid_without_full_verified_payment():
    uow = FakeUnitOfWork()
    order = _order(uow)

    with pytest.raises(ConflictError, match="without full verified payment"):
        UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=ORDER_STATUS_PAID))

    with uow:
        assert uow.orders.get_by_id(order.id).status == ORDER_STATUS_PENDING


def test_order_cannot_be_marked_paid_with_only_the_deposit():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    deposit = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(deposit.payment_id)

    with pytest.raises(ConflictError, match="without full verified payment"):
        UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=ORDER_STATUS_PAID))


def test_order_can_be_marked_paid_when_payments_fully_cover_the_total():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(intent.payment_id)

    # El taller marca `paid` con el anticipo y el saldo ya acreditados aunque el
    # estado logístico siga en `pending` (p. ej. tras una conciliación manual).
    with uow:
        pending = uow.orders.get_by_id(order.id)
        pending.status = ORDER_STATUS_PENDING
        uow.orders.save(pending)
        second = uow.payments.save(
            Payment(
                id=None,
                order_id=order.id,
                type="balance",
                amount=Money("100.00"),
                currency="USD",
                status="completed",
                paypal_order_id="PP-MANUAL",
                paypal_capture_id="CAP-MANUAL",
                created_at=None,
                updated_at=None,
                paid_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()
        assert second.id is not None

    updated = UpdateOrder(uow).execute(
        order.id, UpdateOrderInput(status=ORDER_STATUS_PAID)
    )
    assert updated.status == ORDER_STATUS_PAID


def test_sync_credits_a_cancelled_attempt_captured_in_paypal():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CancelPayment(uow).execute(intent.payment_id)

    # PayPal confirma que el cobro se completó antes de la cancelación local.
    processor.mark_completed_externally(intent.paypal_order_id)

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "completed"
    assert payment.paypal_capture_id == f"CAPTURE-{intent.paypal_order_id}"
    assert processor.capture_calls == []
    with uow:
        assert uow.orders.get_by_id(order.id).status == ORDER_STATUS_PENDING
        assert uow.capture_reservations.active_payment_id(order.id) is None


def test_sync_never_captures_an_approved_order_for_a_cancelled_attempt():
    uow = FakeUnitOfWork()
    order = _order(uow)
    processor = FakePaymentProcessor()
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CancelPayment(uow).execute(intent.payment_id)
    processor.set_order_status(intent.paypal_order_id, "APPROVED")

    payment = SyncPayment(uow, processor).execute(intent.payment_id)

    assert payment.status == "cancelled"
    assert processor.capture_calls == []
    with uow:
        assert uow.capture_reservations.active_payment_id(order.id) is None
