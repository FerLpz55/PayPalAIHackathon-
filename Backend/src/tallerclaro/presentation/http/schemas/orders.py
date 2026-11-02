"""Esquemas Pydantic para pedidos."""

from datetime import date

from pydantic import BaseModel


class OrderResponse(BaseModel):
    id: str
    quote_id: str
    code: str
    total: float
    deposit_amount: float
    balance_amount: float
    currency: str
    status: str
    estimated_delivery_date: date | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    limit: int
    offset: int


class UpdateOrderRequest(BaseModel):
    status: str | None = None
    estimated_delivery_date: date | None = None


class PaymentSummary(BaseModel):
    id: str
    type: str
    amount: float
    status: str
    paypal_order_id: str | None


class OrderDetailResponse(OrderResponse):
    payments: list[PaymentSummary]
    paid_amount: float
    remaining_balance: float
