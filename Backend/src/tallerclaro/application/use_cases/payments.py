"""Casos de uso para pagos."""

from __future__ import annotations

from datetime import datetime, timezone
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
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
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


class CreateOrderPayment:
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
        completed_payments = [p for p in payments if p.status == PAYMENT_STATUS_COMPLETED]
        paid = sum((p.amount.amount for p in completed_payments), Money.zero().amount)
        remaining = order.total.amount - paid

        if payment_type == "deposit":
            amount = order.deposit_amount
        elif payment_type == "balance":
            amount = Money(remaining)
        else:
            raise ValidationDomainError(f"Invalid payment type: {payment_type}")

        if amount.amount > remaining:
            raise ConflictError(f"Payment amount exceeds remaining balance: {remaining}")
        if amount.amount <= 0:
            raise ConflictError("Payment amount must be positive")

        if payment_type == "deposit":
            for p in payments:
                if p.type == "deposit" and p.status == PAYMENT_STATUS_COMPLETED:
                    raise ConflictError("Deposit already paid")

        return amount

    def execute(
        self, order_id: OrderId, payment_type: PaymentType, authorized_quote_id: QuoteId | None = None
    ) -> PaymentIntent:
        with self._uow:
            amount = self._validate_and_compute_amount(order_id, payment_type, authorized_quote_id)

        intent = self._payment_processor.create_order(
            amount=str(amount.amount), currency="USD"
        )

        with self._uow:
            amount = self._validate_and_compute_amount(order_id, payment_type, authorized_quote_id)
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
    def __init__(self, uow: UnitOfWork, payment_processor: PaymentProcessor) -> None:
        self._uow = uow
        self._payment_processor = payment_processor

    def _validate_order_balance_for_capture(self, order: Order, payment: Payment) -> None:
        payments = self._uow.payments.list_by_order(order.id)
        completed_others = [
            p for p in payments
            if p.status == PAYMENT_STATUS_COMPLETED and p.id != payment.id
        ]
        if payment.type == "deposit" and any(p.type == "deposit" for p in completed_others):
            raise ConflictError("Deposit already paid")
        already_paid = sum((p.amount.amount for p in completed_others), Money.zero().amount)
        remaining = order.total.amount - already_paid
        if payment.amount.amount > remaining:
            raise ConflictError(
                f"Payment amount {payment.amount.amount} exceeds remaining balance: {remaining}"
            )

    def execute(
        self, payment_id: PaymentId, authorized_quote_id: QuoteId | None = None
    ) -> CapturedPayment:
        with self._uow:
            payment = self._uow.payments.get_by_id(payment_id)
            if payment is None:
                raise NotFoundError("Payment", payment_id)

            order = self._uow.orders.get_by_id(payment.order_id)
            if order is None:
                raise NotFoundError("Order", payment.order_id)
            if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
                raise ForbiddenError("Not authorized to capture payment for this order")

            if payment.status == PAYMENT_STATUS_COMPLETED:
                return CapturedPayment(
                    payment_id=payment.id,
                    status=payment.status,
                    paypal_order_id=payment.paypal_order_id or "",
                    paypal_capture_id=payment.paypal_capture_id or "",
                    amount=payment.amount.amount,
                    currency=payment.currency,
                    paid_at=payment.paid_at.isoformat() if payment.paid_at else "",
                )

            if payment.status != PAYMENT_STATUS_PENDING:
                raise ConflictError(f"Cannot capture payment in status {payment.status}")

            if payment.paypal_order_id is None:
                raise ConflictError("Payment has no PayPal order")

            self._validate_order_balance_for_capture(order, payment)

            expected_paypal_order_id = payment.paypal_order_id
            expected_amount = payment.amount.amount
            expected_currency = payment.currency

        captured = self._payment_processor.capture_order(expected_paypal_order_id)

        if captured.status != PAYMENT_STATUS_COMPLETED:
            raise ConflictError(f"Captured payment status is not completed: {captured.status}")
        if captured.paypal_order_id != expected_paypal_order_id:
            raise ConflictError("Captured PayPal order ID does not match expected payment")
        if captured.currency != expected_currency:
            raise ConflictError(
                f"Captured currency {captured.currency} does not match expected {expected_currency}"
            )
        try:
            captured_money = Money(Decimal(str(captured.amount)))
        except (InvalidOperation, TypeError, ValueError, ValidationDomainError) as exc:
            raise ConflictError("Captured payment amount is invalid") from exc

        if captured_money.amount != expected_amount:
            raise ConflictError(
                f"Captured amount {captured_money.amount} does not match expected {expected_amount}"
            )
        if not captured.paypal_capture_id or not str(captured.paypal_capture_id).strip():
            raise ConflictError("Captured payment is missing PayPal capture ID")

        with self._uow:
            payment = self._uow.payments.get_by_id(payment_id)
            if payment is None:
                raise NotFoundError("Payment", payment_id)

            order = self._uow.orders.get_by_id(payment.order_id)
            if order is None:
                raise NotFoundError("Order", payment.order_id)
            if authorized_quote_id is not None and order.quote_id != authorized_quote_id:
                raise ForbiddenError("Not authorized to capture payment for this order")

            if payment.status == PAYMENT_STATUS_COMPLETED:
                return CapturedPayment(
                    payment_id=payment.id,
                    status=payment.status,
                    paypal_order_id=payment.paypal_order_id or "",
                    paypal_capture_id=payment.paypal_capture_id or "",
                    amount=payment.amount.amount,
                    currency=payment.currency,
                    paid_at=payment.paid_at.isoformat() if payment.paid_at else "",
                )

            if payment.status != PAYMENT_STATUS_PENDING:
                raise ConflictError(f"Cannot capture payment in status {payment.status}")

            self._validate_order_balance_for_capture(order, payment)

            payment.mark_completed(
                paypal_order_id=captured.paypal_order_id,
                paypal_capture_id=captured.paypal_capture_id,
                paid_at=datetime.fromisoformat(captured.paid_at),
            )
            self._uow.payments.save(payment)

            self._maybe_mark_order_paid(order)
            self._uow.orders.save(order)

            self._uow.commit()
            captured.payment_id = payment.id
            captured.amount = payment.amount.amount
            captured.currency = payment.currency
            return captured

    def _maybe_mark_order_paid(self, order: Order) -> None:
        payments = self._uow.payments.list_by_order(order.id)
        paid = sum(
            (p.amount.amount for p in payments if p.status == PAYMENT_STATUS_COMPLETED),
            Money.zero().amount,
        )
        if paid >= order.total.amount:
            if order.status == ORDER_STATUS_PENDING:
                order.update_status(ORDER_STATUS_PAID)


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
