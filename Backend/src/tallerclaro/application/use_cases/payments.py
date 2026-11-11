"""Casos de uso para pagos.

Los casos siguen el patrón de 3 fases: validar y reservar dentro del UoW,
llamar al proveedor externo fuera de SQL y persistir el resultado en una nueva
transacción. Nunca se ejecuta red dentro de una transacción abierta.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from tallerclaro.application.dtos import CapturedPayment, PaymentIntent
from tallerclaro.application.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from tallerclaro.application.interfaces import PaymentProcessor, UnitOfWork
from tallerclaro.domain.entities import (
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_PENDING,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    PaymentType,
    QuoteId,
)

# Ventana durante la cual un intento pendiente puede reintentarse con la misma
# clave de idempotencia. Pasada la ventana se exige conciliar o cancelar.
PAYMENT_IDEMPOTENCY_WINDOW = timedelta(minutes=15)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _request_fingerprint(
    order_id: OrderId, payment_type: PaymentType, amount: Money, currency: str
) -> str:
    raw = f"{int(order_id)}|{payment_type}|{amount.amount}|{currency}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_verified_usd_amount(raw_amount: object) -> Decimal:
    try:
        captured_amount = Decimal(str(raw_amount))
        if not captured_amount.is_finite() or captured_amount.as_tuple().exponent < -2:
            raise ValueError("invalid USD amount")
        return captured_amount
    except (InvalidOperation, TypeError, ValueError, ValidationDomainError) as exc:
        raise ConflictError("Captured payment amount is invalid") from exc


@dataclass(frozen=True)
class _CaptureExpectation:
    """Datos verificados en Fase 1 que la respuesta de PayPal debe igualar en Fase 2."""

    paypal_order_id: str
    amount: Decimal
    currency: str


def _verify_captured_payload(
    captured: CapturedPayment, expectation: _CaptureExpectation
) -> None:
    if captured.status != PAYMENT_STATUS_COMPLETED:
        raise ConflictError(f"Captured payment status is not completed: {captured.status}")
    if captured.paypal_order_id != expectation.paypal_order_id:
        raise ConflictError("Captured PayPal order ID does not match expected payment")
    if captured.currency != expectation.currency:
        raise ConflictError(
            f"Captured currency {captured.currency} does not match expected {expectation.currency}"
        )

    captured_amount = _parse_verified_usd_amount(captured.amount)
    if captured_amount != expectation.amount:
        raise ConflictError(
            f"Captured amount {captured_amount} does not match expected {expectation.amount}"
        )
    if not captured.paypal_capture_id or not str(captured.paypal_capture_id).strip():
        raise ConflictError("Captured payment is missing PayPal capture ID")


@dataclass(frozen=True)
class _PaymentAttempt:
    """Intento pendiente que se reutiliza o se crea antes de llamar a PayPal."""

    payment_id: PaymentId
    idempotency_key: str
    amount: Money
    paypal_order_id: str | None
    approval_url: str | None

    @property
    def has_provider_order(self) -> bool:
        return bool(self.paypal_order_id)


@dataclass(frozen=True)
class _SyncPlan:
    """Resultado de la Fase 1 de conciliación.

    ``capture_allowed`` solo es cierto para intentos ``pending``: un intento ya
    cancelado o fallido nunca se captura, pero sí se acredita si PayPal informa
    que el cobro se completó igualmente.
    """

    payment: Payment
    expectation: _CaptureExpectation | None = None
    capture_allowed: bool = True


class CreateOrderPayment:
    """Crea una orden de pago en PayPal con idempotencia persistente.

    1. Valida pedido, calcula el importe y reutiliza/crea un intento pendiente
       con clave de idempotencia y huella de la solicitud antes de llamar a
       PayPal.
    2. Crea o recupera la orden en el proveedor fuera de la transacción usando
       ``PayPal-Request-Id``.
    3. Revalida el importe y guarda la orden del proveedor.
    """

    def __init__(self, uow: UnitOfWork, payment_processor: PaymentProcessor) -> None:
        self._uow = uow
        self._payment_processor = payment_processor

    def execute(
        self,
        order_id: OrderId,
        payment_type: PaymentType,
        authorized_quote_id: QuoteId | None = None,
    ) -> PaymentIntent:
        attempt = self._uow.execute_sql(
            lambda uow: self._begin_or_reuse_attempt(
                uow, order_id, payment_type, authorized_quote_id
            )
        )
        if attempt.has_provider_order:
            return self._intent_from_attempt(attempt)

        intent = self._payment_processor.create_order(
            amount=str(attempt.amount.amount),
            currency="USD",
            request_id=attempt.idempotency_key,
        )
        self._verify_provider_intent(intent, attempt.amount)

        return self._uow.execute_sql(
            lambda uow: self._persist_provider_order(
                uow,
                order_id,
                payment_type,
                attempt,
                intent,
                authorized_quote_id,
            )
        )

    def _begin_or_reuse_attempt(
        self,
        uow: UnitOfWork,
        order_id: OrderId,
        payment_type: PaymentType,
        authorized_quote_id: QuoteId | None,
    ) -> _PaymentAttempt:
        order = self._load_authorized_order(uow, order_id, authorized_quote_id)
        amount = self._amount_for_new_payment(uow, order, payment_type)
        fingerprint = _request_fingerprint(order_id, payment_type, amount, "USD")

        active = uow.capture_reservations.active_payment_id(order_id)
        if active is not None:
            raise ConflictError(
                "A capture is in progress for this order; reconcile it before creating another payment"
            )

        pending = uow.payments.get_pending_by_order_and_type(order_id, payment_type)
        if pending is not None:
            self._ensure_attempt_is_reusable(pending, fingerprint, amount)
            return _PaymentAttempt(
                payment_id=pending.id,
                idempotency_key=pending.idempotency_key,
                amount=amount,
                paypal_order_id=pending.paypal_order_id,
                approval_url=pending.approval_url,
            )

        payment = uow.payments.save(
            Payment(
                id=None,
                order_id=order_id,
                type=payment_type,
                amount=amount,
                currency="USD",
                status=PAYMENT_STATUS_PENDING,
                paypal_order_id=None,
                paypal_capture_id=None,
                created_at=None,
                updated_at=None,
                paid_at=None,
                idempotency_key=str(uuid.uuid4()),
                request_fingerprint=fingerprint,
                approval_url=None,
            )
        )
        return _PaymentAttempt(
            payment_id=payment.id,
            idempotency_key=payment.idempotency_key,
            amount=amount,
            paypal_order_id=None,
            approval_url=None,
        )

    def _persist_provider_order(
        self,
        uow: UnitOfWork,
        order_id: OrderId,
        payment_type: PaymentType,
        attempt: _PaymentAttempt,
        intent: PaymentIntent,
        authorized_quote_id: QuoteId | None,
    ) -> PaymentIntent:
        order = self._load_authorized_order(uow, order_id, authorized_quote_id)
        payment = uow.payments.get_by_id(attempt.payment_id)
        if payment is None:
            raise NotFoundError("Payment", attempt.payment_id)
        if payment.status == PAYMENT_STATUS_COMPLETED:
            return self._intent_from_payment(payment)
        if payment.status != PAYMENT_STATUS_PENDING:
            raise ConflictError(
                f"Cannot attach PayPal order to payment in status {payment.status}"
            )

        current_amount = self._amount_for_new_payment(uow, order, payment_type)
        if current_amount != attempt.amount:
            raise ConflictError("Payment amount changed while creating PayPal order")

        payment.attach_provider_order(intent.paypal_order_id, intent.approval_url)
        payment = uow.payments.save(payment)
        return self._intent_from_payment(payment)

    @staticmethod
    def _load_authorized_order(
        uow: UnitOfWork, order_id: OrderId, authorized_quote_id: QuoteId | None
    ) -> Order:
        order = uow.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
            raise ForbiddenError("Not authorized to make payment for this order")
        return order

    @staticmethod
    def _amount_for_new_payment(
        uow: UnitOfWork, order: Order, payment_type: PaymentType
    ) -> Money:
        payments = uow.payments.list_by_order(order.id)
        return order.requested_payment_amount(payment_type, payments)

    @staticmethod
    def _ensure_attempt_is_reusable(
        pending: Payment, fingerprint: str, amount: Money
    ) -> None:
        if pending.id is None or not pending.idempotency_key:
            raise ConflictError(
                "A previous payment attempt has no idempotency key; sync or cancel it before retrying"
            )
        if pending.request_fingerprint != fingerprint:
            raise ConflictError(
                "A different payment attempt is already pending for this order"
            )
        if pending.amount != amount:
            raise ConflictError(
                "Payment amount changed while a previous attempt is pending"
            )
        created_at = pending.created_at
        if created_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if _utcnow() - created_at > PAYMENT_IDEMPOTENCY_WINDOW:
                raise ConflictError(
                    "The previous payment attempt expired; sync or cancel it before retrying"
                )

    @staticmethod
    def _verify_provider_intent(intent: PaymentIntent, amount: Money) -> None:
        if not intent.paypal_order_id or not str(intent.paypal_order_id).strip():
            raise ConflictError("PayPal order ID is missing")
        if intent.currency != "USD":
            raise ConflictError(
                f"PayPal order currency {intent.currency} does not match expected USD"
            )
        if _parse_verified_usd_amount(intent.amount) != amount.amount:
            raise ConflictError("PayPal order amount does not match the requested amount")

    @staticmethod
    def _intent_from_payment(payment: Payment) -> PaymentIntent:
        return PaymentIntent(
            payment_id=payment.id,
            paypal_order_id=payment.paypal_order_id or "",
            amount=payment.amount.amount,
            currency=payment.currency,
            approval_url=payment.approval_url,
        )

    @classmethod
    def _intent_from_attempt(cls, attempt: _PaymentAttempt) -> PaymentIntent:
        return PaymentIntent(
            payment_id=attempt.payment_id,
            paypal_order_id=attempt.paypal_order_id or "",
            amount=attempt.amount.amount,
            currency="USD",
            approval_url=attempt.approval_url,
        )


class CapturePayment:
    """Captura un intento de pago en PayPal usando el patrón transaccional de 3 fases.

    Fase 1: Valida estado/saldo, reserva ``captura_en_curso`` y confirma la reserva.
    Fase 2: Captura y verifica el pago con el proveedor externo fuera de SQL.
    Fase 3: Revalida en una nueva transacción, acredita el pago y libera la reserva.
    """

    def __init__(self, uow: UnitOfWork, payment_processor: PaymentProcessor) -> None:
        self._uow = uow
        self._payment_processor = payment_processor

    def execute(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None = None
    ) -> CapturedPayment:
        already_completed, expectation = self._reserve_capture(payment_id, authorized_quote_id)
        if already_completed is not None or expectation is None:
            return already_completed  # type: ignore[return-value]

        captured = self._capture_and_verify_with_provider(expectation)
        return self._persist_captured_payment(payment_id, captured, authorized_quote_id)

    def _reserve_capture(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> tuple[CapturedPayment | None, _CaptureExpectation | None]:
        def reserve(uow: UnitOfWork) -> tuple[CapturedPayment | None, _CaptureExpectation | None]:
            payment, order = self._load_authorized_payment_and_order(
                uow, payment_id, authorized_quote_id
            )
            if payment.status == PAYMENT_STATUS_COMPLETED:
                return self._to_completed_dto(payment), None

            self._ensure_payment_is_pending(payment)
            if payment.paypal_order_id is None:
                raise ConflictError("Payment has no PayPal order")

            self._validate_order_balance_for_capture(uow, order, payment)

            if not uow.capture_reservations.reserve(order.id, payment.id):
                raise ConflictError("Another capture is in progress for this order")

            expectation = _CaptureExpectation(
                paypal_order_id=payment.paypal_order_id,
                amount=payment.amount.amount,
                currency=payment.currency,
            )
            return None, expectation

        return self._uow.execute_sql(reserve)

    def _capture_and_verify_with_provider(
        self, expectation: _CaptureExpectation
    ) -> CapturedPayment:
        captured = self._payment_processor.capture_order(expectation.paypal_order_id)
        _verify_captured_payload(captured, expectation)
        return captured

    def _persist_captured_payment(
        self,
        payment_id: PaymentId,
        captured: CapturedPayment,
        authorized_quote_id: QuoteId | None,
    ) -> CapturedPayment:
        def persist(uow: UnitOfWork) -> CapturedPayment:
            return self._complete_payment(uow, payment_id, captured, authorized_quote_id)

        return self._uow.execute_sql(persist)

    def _complete_payment(
        self,
        uow: UnitOfWork,
        payment_id: PaymentId,
        captured: CapturedPayment,
        authorized_quote_id: QuoteId | None,
    ) -> CapturedPayment:
        payment, order = self._load_authorized_payment_and_order(
            uow, payment_id, authorized_quote_id
        )
        if payment.status == PAYMENT_STATUS_COMPLETED:
            return self._to_completed_dto(payment)

        self._ensure_payment_can_be_completed(payment)
        self._validate_order_balance_for_capture(uow, order, payment)
        advance_order = payment.status == PAYMENT_STATUS_PENDING

        payment.mark_completed(
            paypal_order_id=captured.paypal_order_id,
            paypal_capture_id=captured.paypal_capture_id,
            paid_at=datetime.fromisoformat(captured.paid_at),
        )
        uow.payments.save(payment)

        if advance_order:
            self._maybe_mark_order_paid(uow, order)
        uow.orders.save(order)
        uow.capture_reservations.release(order.id, payment.id)

        captured.payment_id = payment.id
        captured.amount = payment.amount.amount
        captured.currency = payment.currency
        return captured

    @staticmethod
    def _load_authorized_payment_and_order(
        uow: UnitOfWork, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> tuple[Payment, Order]:
        payment = uow.payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)

        order = uow.orders.get_by_id(payment.order_id)
        if order is None:
            raise NotFoundError("Order", payment.order_id)
        if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
            raise ForbiddenError("Not authorized to capture payment for this order")

        return payment, order

    @staticmethod
    def _validate_order_balance_for_capture(
        uow: UnitOfWork, order: Order, payment: Payment
    ) -> None:
        payments = uow.payments.list_by_order(order.id)
        order.validate_capture(payment, payments)

    @staticmethod
    def _maybe_mark_order_paid(uow: UnitOfWork, order: Order) -> None:
        payments = uow.payments.list_by_order(order.id)
        order.advance_after_payment(payments)

    @staticmethod
    def _ensure_payment_is_pending(payment: Payment) -> None:
        if payment.status != PAYMENT_STATUS_PENDING:
            raise ConflictError(f"Cannot capture payment in status {payment.status}")

    @staticmethod
    def _ensure_payment_can_be_completed(payment: Payment) -> None:
        """Acredita una captura verificada incluso si el intento local se cerró."""
        if payment.status not in {
            PAYMENT_STATUS_PENDING,
            PAYMENT_STATUS_CANCELLED,
            PAYMENT_STATUS_FAILED,
        }:
            raise ConflictError(f"Cannot capture payment in status {payment.status}")

    @staticmethod
    def _to_completed_dto(payment: Payment) -> CapturedPayment:
        return CapturedPayment(
            payment_id=payment.id,
            status=payment.status,
            paypal_order_id=payment.paypal_order_id or "",
            paypal_capture_id=payment.paypal_capture_id or "",
            amount=payment.amount.amount,
            currency=payment.currency,
            paid_at=payment.paid_at.isoformat() if payment.paid_at else "",
        )


class SyncPayment:
    """Reconcilia un intento de pago con el estado real de PayPal.

    ``GET`` nunca captura por sí solo. Solo se captura cuando PayPal informa
    ``APPROVED`` y el intento local sigue ``pending``; si ya está ``COMPLETED``
    se persiste esa captura aunque el intento local se hubiera cancelado; si
    está ``VOIDED`` se cancela localmente. Cualquier otro estado libera la
    reserva sin cambiar el intento. Ante un fallo de transporte se mantiene la
    reserva porque el resultado es incierto.
    """

    def __init__(self, uow: UnitOfWork, payment_processor: PaymentProcessor) -> None:
        self._uow = uow
        self._payment_processor = payment_processor

    def execute(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None = None
    ) -> Payment:
        plan = self._uow.execute_sql(
            lambda uow: self._prepare_sync(uow, payment_id, authorized_quote_id)
        )
        if plan.expectation is None:
            return plan.payment

        provider = self._payment_processor.get_order(plan.expectation.paypal_order_id)
        self._verify_provider_order(provider, plan.expectation)

        if provider.status == "COMPLETED":
            captured = provider.capture
            if captured is None:
                raise ConflictError("PayPal reports a completed order without capture data")
            _verify_captured_payload(captured, plan.expectation)
            return self._persist_completed(payment_id, captured, authorized_quote_id)

        if provider.status == "APPROVED":
            if not plan.capture_allowed:
                # El intento local está cerrado: no se cobra sin una acción
                # explícita del cliente, solo se informa el estado real.
                return self._release_and_reload(payment_id, authorized_quote_id)
            captured = self._payment_processor.capture_order(
                plan.expectation.paypal_order_id
            )
            _verify_captured_payload(captured, plan.expectation)
            return self._persist_completed(payment_id, captured, authorized_quote_id)

        if provider.status == "VOIDED":
            return self._persist_cancelled(payment_id, authorized_quote_id)

        return self._release_and_reload(payment_id, authorized_quote_id)

    def _prepare_sync(
        self, uow: UnitOfWork, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> _SyncPlan:
        payment, order = CapturePayment._load_authorized_payment_and_order(
            uow, payment_id, authorized_quote_id
        )
        if payment.status == PAYMENT_STATUS_COMPLETED:
            return _SyncPlan(payment=payment)
        if payment.status not in {
            PAYMENT_STATUS_PENDING,
            PAYMENT_STATUS_CANCELLED,
            PAYMENT_STATUS_FAILED,
        }:
            raise ConflictError(f"Cannot sync payment in status {payment.status}")
        if payment.paypal_order_id is None:
            if payment.status == PAYMENT_STATUS_PENDING:
                raise ConflictError("Payment has no PayPal order to reconcile")
            return _SyncPlan(payment=payment)

        # Un intento cerrado solo se consulta para detectar un cobro ya
        # completado en PayPal; nunca se vuelve a capturar.
        CapturePayment._validate_order_balance_for_capture(uow, order, payment)
        if not uow.capture_reservations.reserve(order.id, payment.id):
            raise ConflictError("Another capture is in progress for this order")

        return _SyncPlan(
            payment=payment,
            expectation=_CaptureExpectation(
                paypal_order_id=payment.paypal_order_id,
                amount=payment.amount.amount,
                currency=payment.currency,
            ),
            capture_allowed=payment.status == PAYMENT_STATUS_PENDING,
        )

    @staticmethod
    def _verify_provider_order(provider, expectation: _CaptureExpectation) -> None:
        if provider.paypal_order_id != expectation.paypal_order_id:
            raise ConflictError("PayPal order ID does not match expected payment")

    def _persist_completed(
        self,
        payment_id: PaymentId,
        captured: CapturedPayment,
        authorized_quote_id: QuoteId | None,
    ) -> Payment:
        def persist(uow: UnitOfWork) -> Payment:
            CapturePayment(self._uow, self._payment_processor)._complete_payment(
                uow, payment_id, captured, authorized_quote_id
            )
            payment = uow.payments.get_by_id(payment_id)
            if payment is None:
                raise NotFoundError("Payment", payment_id)
            return payment

        return self._uow.execute_sql(persist)

    def _persist_cancelled(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> Payment:
        def persist(uow: UnitOfWork) -> Payment:
            payment, order = CapturePayment._load_authorized_payment_and_order(
                uow, payment_id, authorized_quote_id
            )
            if payment.status == PAYMENT_STATUS_COMPLETED:
                return payment
            if payment.status != PAYMENT_STATUS_CANCELLED:
                payment.mark_cancelled()
                payment = uow.payments.save(payment)
            uow.capture_reservations.release(order.id, payment.id)
            return payment

        return self._uow.execute_sql(persist)

    def _release_and_reload(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> Payment:
        def release(uow: UnitOfWork) -> Payment:
            payment, order = CapturePayment._load_authorized_payment_and_order(
                uow, payment_id, authorized_quote_id
            )
            uow.capture_reservations.release(order.id, payment.id)
            return payment

        return self._uow.execute_sql(release)


class CancelPayment:
    """Cancela un intento pendiente sin liberar reservas de captura inciertas."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None = None
    ) -> Payment:
        def cancel(uow: UnitOfWork) -> Payment:
            payment, order = CapturePayment._load_authorized_payment_and_order(
                uow, payment_id, authorized_quote_id
            )
            if payment.status == PAYMENT_STATUS_COMPLETED:
                raise ConflictError("Cannot cancel a completed payment")
            if payment.status == PAYMENT_STATUS_CANCELLED:
                return payment
            if uow.capture_reservations.active_payment_id(order.id) is not None:
                raise ConflictError(
                    "A capture is in progress; reconcile it before cancelling"
                )

            payment.mark_cancelled()
            return uow.payments.save(payment)

        return self._uow.execute_sql(cancel)


class GetPayment:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, payment_id: PaymentId, authorized_quote_id: QuoteId | None = None) -> Payment:
        with self._uow:
            payment = self._uow.payments.get_by_id(payment_id)
            if payment is None:
                raise NotFoundError("Payment", payment_id)

            if authorized_quote_id is not None:
                order = self._uow.orders.get_by_id(payment.order_id)
                if order is None:
                    raise NotFoundError("Order", payment.order_id)
                if order.quote_id != authorized_quote_id:
                    raise ForbiddenError("Not authorized to access this payment")

            return payment
