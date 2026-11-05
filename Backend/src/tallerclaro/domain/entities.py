"""Entidades y objetos de valor del dominio."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import NewType

from tallerclaro.domain.exceptions import ConflictError, ValidationDomainError
from tallerclaro.domain.value_objects import Money

QuoteId = NewType("QuoteId", int)
OrderId = NewType("OrderId", int)
PaymentId = NewType("PaymentId", int)
CustomerId = NewType("CustomerId", int)
CarpenterId = NewType("CarpenterId", int)
QuoteLineItemId = NewType("QuoteLineItemId", int)

QUOTE_STATUS_DRAFT = "draft"
QUOTE_STATUS_NEEDS_INFORMATION = "needs_information"
QUOTE_STATUS_PENDING_REVIEW = "pending_review"
QUOTE_STATUS_APPROVED = "approved"
QUOTE_STATUS_REJECTED = "rejected"
QuoteStatus = str

ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_PAID = "paid"
ORDER_STATUS_IN_PROGRESS = "in_progress"
ORDER_STATUS_DELIVERED = "delivered"
OrderStatus = str

PAYMENT_TYPE_DEPOSIT = "deposit"
PAYMENT_TYPE_BALANCE = "balance"
PaymentType = str

PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_COMPLETED = "completed"
PAYMENT_STATUS_FAILED = "failed"
PAYMENT_STATUS_CANCELLED = "cancelled"
PaymentStatus = str

LINE_ITEM_TYPE_MATERIAL = "material"
LINE_ITEM_TYPE_LABOR = "labor"
LINE_ITEM_TYPE_OTHER = "other"
LineItemType = str

DEPOSIT_PERCENTAGE = Decimal("0.50")


@dataclass
class Customer:
    id: CustomerId | None
    name: str
    email: str
    phone: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Carpenter:
    id: CarpenterId | None
    name: str
    workshop_name: str
    email: str
    phone: str | None
    created_at: datetime | None = None


@dataclass(frozen=True)
class QuoteLineItem:
    id: QuoteLineItemId | None
    type: LineItemType
    description: str
    unit: str
    quantity: Decimal
    unit_price: Money

    def __post_init__(self) -> None:
        if self.quantity <= Decimal("0"):
            raise ValidationDomainError("Quantity must be positive")
        if not self.unit_price.is_non_negative():
            raise ValidationDomainError("Unit price cannot be negative")

    @property
    def amount(self) -> Money:
        return Money(self.quantity * self.unit_price.amount)


@dataclass
class Quote:
    id: QuoteId | None
    customer_id: CustomerId
    carpenter_id: CarpenterId
    request: str
    description: str | None
    line_items: list[QuoteLineItem] = field(default_factory=list)
    total: Money | None = None
    status: QuoteStatus = QUOTE_STATUS_DRAFT
    currency: str = "USD"
    assumptions: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ValidationDomainError("Currency must be USD")

    def recalculate_total(self) -> None:
        self.total = Money(sum((item.amount.amount for item in self.line_items), Decimal("0")))

    @property
    def deposit_amount(self) -> Money | None:
        if self.total is None:
            return None
        return Money(self.total.amount * DEPOSIT_PERCENTAGE)

    @property
    def balance_amount(self) -> Money | None:
        if self.total is None or self.deposit_amount is None:
            return None
        return self.total - self.deposit_amount

    def mark_needs_information(self, missing_info: list[str]) -> None:
        self.status = QUOTE_STATUS_NEEDS_INFORMATION
        self.missing_info = list(missing_info)
        self.assumptions = []


    def submit_for_review(self) -> None:
        if self.total is None or not self.total.is_positive():
            raise ValidationDomainError("Quote must have a positive total before review")
        if not self.line_items:
            raise ValidationDomainError("Quote must have line items before review")
        if self.status not in {QUOTE_STATUS_DRAFT, QUOTE_STATUS_NEEDS_INFORMATION, QUOTE_STATUS_PENDING_REVIEW}:
            raise ConflictError(f"Cannot submit quote from status {self.status}")
        self.status = QUOTE_STATUS_PENDING_REVIEW
        self.missing_info = []



    def approve(self) -> None:
        if self.status != QUOTE_STATUS_PENDING_REVIEW:
            raise ConflictError(f"Quote must be in pending_review to be approved, current: {self.status}")
        self.status = QUOTE_STATUS_APPROVED

    def reject(self) -> None:
        if self.status != QUOTE_STATUS_PENDING_REVIEW:
            raise ConflictError(f"Quote must be in pending_review to be rejected, current: {self.status}")
        self.status = QUOTE_STATUS_REJECTED


@dataclass
class Order:
    id: OrderId | None
    quote_id: QuoteId
    carpenter_id: CarpenterId
    code: str
    total: Money
    deposit_amount: Money
    currency: str
    status: OrderStatus
    created_at: datetime | None
    updated_at: datetime | None
    estimated_delivery_date: date | None = None

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ValidationDomainError("Currency must be USD")
        if self.deposit_amount > self.total:
            raise ValidationDomainError("Deposit cannot exceed total")

    def update_status(self, new_status: OrderStatus, estimated_delivery_date: date | None = None) -> None:
        valid_transitions: dict[OrderStatus, set[OrderStatus]] = {
            ORDER_STATUS_PENDING: {ORDER_STATUS_PAID, ORDER_STATUS_IN_PROGRESS},
            ORDER_STATUS_PAID: {ORDER_STATUS_IN_PROGRESS},
            ORDER_STATUS_IN_PROGRESS: {ORDER_STATUS_DELIVERED},
            ORDER_STATUS_DELIVERED: set(),
        }
        allowed = valid_transitions.get(self.status, set())
        if new_status not in allowed:
            raise ConflictError(f"Cannot transition order from {self.status} to {new_status}")
        self.status = new_status
        if estimated_delivery_date is not None:
            self.estimated_delivery_date = estimated_delivery_date

    def can_deliver(self) -> bool:
        return self.status == ORDER_STATUS_IN_PROGRESS

    @property
    def balance_amount(self) -> Money:
        return self.total - self.deposit_amount

    def calculate_paid_amount(self, payments: list[Payment]) -> Money:
        paid = sum(
            (p.amount.amount for p in payments if p.status == PAYMENT_STATUS_COMPLETED),
            Decimal("0"),
        )
        return Money(paid)

    def calculate_remaining_balance(self, payments: list[Payment]) -> Money:
        paid = self.calculate_paid_amount(payments)
        if paid.amount >= self.total.amount:
            return Money.zero()
        return self.total - paid

    def is_fully_paid(self, payments: list[Payment]) -> bool:
        return self.calculate_paid_amount(payments).amount >= self.total.amount

    def _completed_deposit_exists(self, payments: list[Payment]) -> bool:
        return any(
            p.type == PAYMENT_TYPE_DEPOSIT and p.status == PAYMENT_STATUS_COMPLETED
            for p in payments
        )

    def requested_payment_amount(
        self, payment_type: PaymentType, payments: list[Payment]
    ) -> Money:
        """Importe que corresponde solicitar para un nuevo intento de pago.

        Precondiciones: ``payments`` son los intentos del propio pedido.
        Devuelve el anticipo o el saldo pendiente y valida que exista saldo,
        que el importe sea positivo y que no se repita un anticipo completado.
        """
        if payment_type not in {PAYMENT_TYPE_DEPOSIT, PAYMENT_TYPE_BALANCE}:
            raise ValidationDomainError(f"Invalid payment type: {payment_type}")

        remaining = self.calculate_remaining_balance(payments)
        amount = self.deposit_amount if payment_type == PAYMENT_TYPE_DEPOSIT else remaining

        if amount > remaining:
            raise ConflictError(f"Payment amount exceeds remaining balance: {remaining.amount}")
        if not amount.is_positive():
            raise ConflictError("Payment amount must be positive")
        if payment_type == PAYMENT_TYPE_DEPOSIT and self._completed_deposit_exists(payments):
            raise ConflictError("Deposit already paid")
        return amount

    def validate_capture(self, payment: Payment, payments: list[Payment]) -> None:
        """Valida que un intento pendiente pueda capturarse contra el saldo actual.

        ``payments`` son los intentos del pedido; el propio ``payment`` no cuenta
        como pagado todavía. Lanza ``ConflictError`` si el anticipo ya se pagó o
        si el importe supera el saldo restante tras otros pagos completados.
        """
        completed_others = [
            p
            for p in payments
            if p.status == PAYMENT_STATUS_COMPLETED and p.id != payment.id
        ]
        if payment.type == PAYMENT_TYPE_DEPOSIT and any(
            p.type == PAYMENT_TYPE_DEPOSIT for p in completed_others
        ):
            raise ConflictError("Deposit already paid")

        already_paid = sum((p.amount.amount for p in completed_others), Decimal("0"))
        remaining = Money(self.total.amount - already_paid)
        if payment.amount > remaining:
            raise ConflictError(
                f"Payment amount {payment.amount.amount} exceeds remaining balance: {remaining.amount}"
            )


@dataclass
class Payment:
    id: PaymentId | None
    order_id: OrderId
    type: PaymentType
    amount: Money
    currency: str
    status: PaymentStatus
    paypal_order_id: str | None
    paypal_capture_id: str | None
    created_at: datetime | None
    updated_at: datetime | None
    paid_at: datetime | None

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise ValidationDomainError("Currency must be USD")

    def mark_completed(self, paypal_order_id: str, paypal_capture_id: str, paid_at: datetime) -> None:
        if self.status == PAYMENT_STATUS_COMPLETED:
            return
        if self.status != PAYMENT_STATUS_PENDING:
            raise ConflictError(f"Cannot complete payment from status {self.status}")
        self.status = PAYMENT_STATUS_COMPLETED
        self.paypal_order_id = paypal_order_id
        self.paypal_capture_id = paypal_capture_id
        self.paid_at = paid_at

    def mark_failed(self) -> None:
        if self.status == PAYMENT_STATUS_COMPLETED:
            raise ConflictError("Cannot mark a completed payment as failed")
        self.status = PAYMENT_STATUS_FAILED

    def mark_cancelled(self) -> None:
        if self.status == PAYMENT_STATUS_COMPLETED:
            raise ConflictError("Cannot cancel a completed payment")
        self.status = PAYMENT_STATUS_CANCELLED
