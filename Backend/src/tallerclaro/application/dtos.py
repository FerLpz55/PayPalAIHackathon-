"""DTOs internos de la capa de aplicación."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from tallerclaro.domain.entities import (
    CarpenterId,
    CustomerId,
    LineItemType,
    OrderId,
    PaymentId,
    QuoteId,
)


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
