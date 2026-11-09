"""Webhooks de PayPal y conciliación periódica (Fase E)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tallerclaro.application.dtos import WebhookEvent
from tallerclaro.application.exceptions import DomainError
from tallerclaro.application.use_cases import (
    CreateOrderPayment,
    HandlePayPalWebhook,
    ReconcileStalePayments,
)
from tallerclaro.domain.entities import (
    ORDER_STATUS_PENDING,
    CarpenterId,
    Money,
    Order,
    QuoteId,
)
from tests.fakes import FakePaymentProcessor, FakeUnitOfWork, FakeWebhookVerifier


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


def _approved_attempt(uow: FakeUnitOfWork, processor: FakePaymentProcessor):
    order = _order(uow)
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    processor.set_order_status(intent.paypal_order_id, "APPROVED")
    return order, intent


def _capture_event(event_id: str, paypal_order_id: str) -> WebhookEvent:
    return WebhookEvent(
        id=event_id,
        type="PAYMENT.CAPTURE.COMPLETED",
        paypal_order_id=paypal_order_id,
    )


class _FlakyProcessor(FakePaymentProcessor):
    def __init__(self) -> None:
        super().__init__()
        self.fail_reads = True

    def get_order(self, paypal_order_id):
        if self.fail_reads:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal transport unavailable; retry reconciliation",
            )
        return super().get_order(paypal_order_id)


def test_verified_webhook_reconciles_the_payment():
    uow = FakeUnitOfWork()
    processor = FakePaymentProcessor()
    order, intent = _approved_attempt(uow, processor)
    verifier = FakeWebhookVerifier()
    verifier.queue(_capture_event("WH-1", intent.paypal_order_id))

    outcome = HandlePayPalWebhook(uow, verifier, processor).execute(
        {"paypal-transmission-id": "t-1"}, b'{"id": "WH-1"}'
    )

    assert outcome == "processed"
    assert verifier.calls[0][0] == {"paypal-transmission-id": "t-1"}
    assert verifier.calls[0][1] == b'{"id": "WH-1"}'
    with uow:
        payment = uow.payments.get_by_id(intent.payment_id)
        assert payment.status == "completed"
        assert payment.paypal_capture_id == f"CAPTURE-{intent.paypal_order_id}"
        assert uow.paypal_events.state("WH-1") == "processed"
        assert "completed" in (uow.paypal_events.detail("WH-1") or "")


def test_repeated_delivery_is_deduplicated_without_reconciling_again():
    uow = FakeUnitOfWork()
    processor = FakePaymentProcessor()
    _, intent = _approved_attempt(uow, processor)
    verifier = FakeWebhookVerifier()
    event = _capture_event("WH-1", intent.paypal_order_id)
    verifier.queue(event)

    first = HandlePayPalWebhook(uow, verifier, processor).execute({}, b"{}")
    captures_after_first = len(processor.capture_calls)
    verifier.queue(event)
    second = HandlePayPalWebhook(uow, verifier, processor).execute({}, b"{}")

    assert first == "processed"
    assert second == "duplicate"
    assert len(processor.capture_calls) == captures_after_first


def test_failed_delivery_can_be_retried_by_paypal():
    uow = FakeUnitOfWork()
    processor = _FlakyProcessor()
    _, intent = _approved_attempt(uow, processor)
    verifier = FakeWebhookVerifier()
    event = _capture_event("WH-RETRY", intent.paypal_order_id)

    verifier.queue(event)
    with pytest.raises(DomainError):
        HandlePayPalWebhook(uow, verifier, processor).execute({}, b"{}")

    with uow:
        assert uow.paypal_events.state("WH-RETRY") == "failed"

    processor.fail_reads = False
    verifier.queue(event)
    outcome = HandlePayPalWebhook(uow, verifier, processor).execute({}, b"{}")

    assert outcome == "processed"
    with uow:
        assert uow.paypal_events.state("WH-RETRY") == "processed"
        assert uow.payments.get_by_id(intent.payment_id).status == "completed"


def test_unknown_order_is_recorded_as_ignored():
    uow = FakeUnitOfWork()
    verifier = FakeWebhookVerifier()
    verifier.queue(_capture_event("WH-UNKNOWN", "PP-DOES-NOT-EXIST"))

    outcome = HandlePayPalWebhook(uow, verifier, FakePaymentProcessor()).execute({}, b"{}")

    assert outcome == "ignored"
    with uow:
        assert uow.paypal_events.state("WH-UNKNOWN") == "ignored"


def test_out_of_scope_event_is_ignored():
    uow = FakeUnitOfWork()
    verifier = FakeWebhookVerifier()
    verifier.queue(
        WebhookEvent(id="WH-REFUND", type="PAYMENT.CAPTURE.REFUNDED", paypal_order_id="PP-1")
    )

    outcome = HandlePayPalWebhook(uow, verifier, FakePaymentProcessor()).execute({}, b"{}")

    assert outcome == "ignored"
    with uow:
        assert "outside this release" in (uow.paypal_events.detail("WH-REFUND") or "")


# --- Conciliación periódica ---


def _age_payment(uow: FakeUnitOfWork, payment_id, minutes: int) -> None:
    with uow:
        payment = uow.payments.get_by_id(payment_id)
        payment.updated_at = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        uow.commit()


def test_stale_pending_payment_is_reconciled_in_the_background():
    uow = FakeUnitOfWork()
    processor = FakePaymentProcessor()
    _, intent = _approved_attempt(uow, processor)
    _age_payment(uow, intent.payment_id, minutes=30)

    results = ReconcileStalePayments(
        lambda: uow, processor, min_age_seconds=300, batch_size=10
    ).execute()

    assert results == {
        "checked": 1,
        "completed": 1,
        "cancelled": 0,
        "pending": 0,
        "failed": 0,
    }
    with uow:
        assert uow.payments.get_by_id(intent.payment_id).status == "completed"


def test_recent_pending_payment_is_left_for_the_request_path():
    uow = FakeUnitOfWork()
    processor = FakePaymentProcessor()
    _, intent = _approved_attempt(uow, processor)

    results = ReconcileStalePayments(
        lambda: uow, processor, min_age_seconds=300, batch_size=10
    ).execute()

    assert results["checked"] == 0
    assert processor.capture_calls == []
    with uow:
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"


def test_reconciliation_failure_does_not_abort_the_batch():
    uow = FakeUnitOfWork()
    processor = _FlakyProcessor()
    _, intent = _approved_attempt(uow, processor)
    _age_payment(uow, intent.payment_id, minutes=30)

    results = ReconcileStalePayments(
        lambda: uow, processor, min_age_seconds=300, batch_size=10
    ).execute()

    assert results["failed"] == 1
    assert results["completed"] == 0
    with uow:
        assert uow.payments.get_by_id(intent.payment_id).status == "pending"
        # La reserva se mantiene mientras el resultado del proveedor es incierto.
        assert (
            uow.capture_reservations.active_payment_id(intent.payment_id)
            is not None
        )
