"""DTOs internos de la capa de aplicación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from tallerclaro.domain.accounting import WorkshopFinancialSummary
from tallerclaro.domain.entities import (
    CarpenterId,
    CustomerId,
    LineItemType,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    Quote,
    QuoteId,
)


@dataclass
class AccessPrincipal:
    kind: Literal["customer", "workshop"]
    customer_id: CustomerId | None = None
    quote_id: QuoteId | None = None
    carpenter_id: CarpenterId | None = None

    @property
    def is_workshop(self) -> bool:
        return self.kind == "workshop"

    @property
    def is_customer(self) -> bool:
        return self.kind == "customer"

    @property
    def role(self) -> str:
        return self.kind

    def __getitem__(self, index: int):
        if index == 0:
            return self.customer_id
        if index == 1:
            return self.quote_id
        raise IndexError(f"Index {index} out of range")

    def __iter__(self):
        yield self.customer_id
        yield self.quote_id


@dataclass
class CreatedQuoteResult:
    quote: Quote
    customer_token: str

    def __getattr__(self, name: str):
        return getattr(self.quote, name)


@dataclass
class CustomerContext:
    """Recursos vinculados al token de un cliente autorizado."""

    quote: Quote
    order: Order | None
    payments: list[Payment]


@dataclass
class OrderDetailResult:
    order: Order
    payments: list[Payment]
    customer_name: str | None
    customer_email: str | None
    project_request: str | None
    paid_amount: Money | None = None
    remaining_balance: Money | None = None

    def __post_init__(self) -> None:
        if self.paid_amount is None:
            self.paid_amount = self.order.calculate_paid_amount(self.payments)
        if self.remaining_balance is None:
            self.remaining_balance = self.order.calculate_remaining_balance(self.payments)

    def __getattr__(self, name: str):
        return getattr(self.order, name)




@dataclass
class CustomerInput:
    name: str
    email: str
    phone: str | None


@dataclass
class CreateQuoteInput:
    customer: CustomerInput
    carpenter_id: CarpenterId
    request: str


@dataclass
class QuoteLineItemInput:
    type: LineItemType
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal


@dataclass
class QuoteProposalResult:
    description: str
    line_items: list[QuoteLineItemInput]
    assumptions: list[str] | None = None
    needs_information: bool = False
    missing_info: list[str] | None = None
    raw_response: str | None = None
    suggested_products: list[MarketPriceReference] | None = None


@dataclass
class OrderListItem:
    id: OrderId
    quote_id: QuoteId
    customer_id: CustomerId
    code: str
    total: Decimal
    deposit_amount: Decimal
    status: str
    created_at: str


@dataclass
class UpdateOrderInput:
    status: str | None = None
    estimated_delivery_date: date | None = None


@dataclass
class PaymentIntent:
    payment_id: PaymentId
    paypal_order_id: str
    amount: Decimal
    currency: str
    approval_url: str | None


@dataclass
class CapturedPayment:
    payment_id: PaymentId
    status: str
    paypal_order_id: str
    paypal_capture_id: str
    amount: Decimal
    currency: str
    paid_at: str


@dataclass(frozen=True)
class AccountingAnswer:
    question: str
    answer: str
    summary: WorkshopFinancialSummary


@dataclass(frozen=True)
class MarketPriceReference:
    title: str
    price_usd: Decimal
    source: str
    url: str | None = None
    image_url: str | None = None
