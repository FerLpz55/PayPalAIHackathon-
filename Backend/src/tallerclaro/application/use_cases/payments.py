"""Casos de uso para pagos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_STATUS_PENDING,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    PaymentType,
    QuoteId,
)


@dataclass(frozen=True)
class _CaptureExpectation:
    """Datos verificados en Fase 1 que la respuesta de PayPal debe igualar en Fase 2."""

    paypal_order_id: str
    amount: Decimal
    currency: str


class CreateOrderPayment:
    """Crea una orden de pago en PayPal y registra el intento pendiente.

    Sigue el patrón de 3 fases sin llamadas de red dentro de transacciones SQL:
    1. Valida pedido y calcula el importe exigible dentro del UoW.
    2. Crea la orden en el procesador de pagos fuera de la transacción.
    3. Revalida que el importe no haya cambiado y guarda el intento en una nueva transacción.
    """

    def __init__(self, uow: UnitOfWork, payment_processor: PaymentProcessor) -> None:
        self._uow = uow
        self._payment_processor = payment_processor

    def _validate_and_compute_amount(
        self, order_id: OrderId, payment_type: PaymentType, authorized_quote_id: QuoteId | None
    ) -> Money:
        order = self._uow.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
            raise ForbiddenError("Not authorized to make payment for this order")

        payments = self._uow.payments.list_by_order(order_id)
        return order.requested_payment_amount(payment_type, payments)

    def execute(
        self, order_id: OrderId, payment_type: PaymentType, authorized_quote_id: QuoteId | None = None
    ) -> PaymentIntent:
        # Fase 1: Validar pedido y calcular el monto permitido.
        with self._uow:
            amount = self._validate_and_compute_amount(order_id, payment_type, authorized_quote_id)

        # Fase 2: Crear la orden en el proveedor externo fuera de la transacción SQL.
        intent = self._payment_processor.create_order(
            amount=str(amount.amount), currency="USD"
        )

        # Fase 3: Revalidar el monto y persistir el intento pendiente.
        with self._uow:
            current_amount = self._validate_and_compute_amount(order_id, payment_type, authorized_quote_id)
            if current_amount != amount:
                raise ConflictError("Payment amount changed while creating PayPal order")

            payment = Payment(
                id=None,
                order_id=order_id,
                type=payment_type,
                amount=amount,
                currency="USD",
                status=PAYMENT_STATUS_PENDING,
                paypal_order_id=intent.paypal_order_id,
                paypal_capture_id=None,
                created_at=None,
                updated_at=None,
                paid_at=None,
            )
            payment = self._uow.payments.save(payment)
            self._uow.commit()

            return PaymentIntent(
                payment_id=payment.id,
                paypal_order_id=intent.paypal_order_id,
                amount=amount.amount,
                currency="USD",
                approval_url=intent.approval_url,
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
        with self._uow:
            payment, order = self._load_authorized_payment_and_order(payment_id, authorized_quote_id)
            if payment.status == PAYMENT_STATUS_COMPLETED:
                return self._to_completed_dto(payment), None

            self._ensure_payment_is_pending(payment)
            if payment.paypal_order_id is None:
                raise ConflictError("Payment has no PayPal order")

            self._validate_order_balance_for_capture(order, payment)

            if not self._uow.capture_reservations.reserve(order.id, payment.id):
                raise ConflictError("Another capture is in progress for this order")

            expectation = _CaptureExpectation(
                paypal_order_id=payment.paypal_order_id,
                amount=payment.amount.amount,
                currency=payment.currency,
            )
            self._uow.commit()
            return None, expectation

    def _capture_and_verify_with_provider(
        self, expectation: _CaptureExpectation
    ) -> CapturedPayment:
        captured = self._payment_processor.capture_order(expectation.paypal_order_id)
        self._verify_captured_payload(captured, expectation)
        return captured

    def _persist_captured_payment(
        self,
        payment_id: PaymentId,
        captured: CapturedPayment,
        authorized_quote_id: QuoteId | None,
    ) -> CapturedPayment:
        with self._uow:
            payment, order = self._load_authorized_payment_and_order(payment_id, authorized_quote_id)
            if payment.status == PAYMENT_STATUS_COMPLETED:
                return self._to_completed_dto(payment)

            self._ensure_payment_is_pending(payment)
            self._validate_order_balance_for_capture(order, payment)

            payment.mark_completed(
                paypal_order_id=captured.paypal_order_id,
                paypal_capture_id=captured.paypal_capture_id,
                paid_at=datetime.fromisoformat(captured.paid_at),
            )
            self._uow.payments.save(payment)

            self._maybe_mark_order_paid(order)
            self._uow.orders.save(order)
            self._uow.capture_reservations.release(order.id, payment.id)
            self._uow.commit()

            captured.payment_id = payment.id
            captured.amount = payment.amount.amount
            captured.currency = payment.currency
            return captured

    def _load_authorized_payment_and_order(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None
    ) -> tuple[Payment, Order]:
        payment = self._uow.payments.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("Payment", payment_id)

        order = self._uow.orders.get_by_id(payment.order_id)
        if order is None:
            raise NotFoundError("Order", payment.order_id)
        if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
            raise ForbiddenError("Not authorized to capture payment for this order")

        return payment, order

    def _validate_order_balance_for_capture(self, order: Order, payment: Payment) -> None:
        payments = self._uow.payments.list_by_order(order.id)
        order.validate_capture(payment, payments)

    def _maybe_mark_order_paid(self, order: Order) -> None:
        payments = self._uow.payments.list_by_order(order.id)
        order.advance_after_payment(payments)

    @staticmethod
    def _ensure_payment_is_pending(payment: Payment) -> None:
        if payment.status != PAYMENT_STATUS_PENDING:
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

    @classmethod
    def _verify_captured_payload(
        cls, captured: CapturedPayment, expectation: _CaptureExpectation
    ) -> None:
        if captured.status != PAYMENT_STATUS_COMPLETED:
            raise ConflictError(f"Captured payment status is not completed: {captured.status}")
        if captured.paypal_order_id != expectation.paypal_order_id:
            raise ConflictError("Captured PayPal order ID does not match expected payment")
        if captured.currency != expectation.currency:
            raise ConflictError(
                f"Captured currency {captured.currency} does not match expected {expectation.currency}"
            )

        captured_amount = cls._parse_verified_usd_amount(captured.amount)
        if captured_amount != expectation.amount:
            raise ConflictError(
                f"Captured amount {captured_amount} does not match expected {expectation.amount}"
            )
        if not captured.paypal_capture_id or not str(captured.paypal_capture_id).strip():
            raise ConflictError("Captured payment is missing PayPal capture ID")

    @staticmethod
    def _parse_verified_usd_amount(raw_amount: object) -> Decimal:
        try:
            captured_amount = Decimal(str(raw_amount))
            if not captured_amount.is_finite() or captured_amount.as_tuple().exponent < -2:
                raise ValueError("invalid USD amount")
            return captured_amount
        except (InvalidOperation, TypeError, ValueError, ValidationDomainError) as exc:
            raise ConflictError("Captured payment amount is invalid") from exc


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
