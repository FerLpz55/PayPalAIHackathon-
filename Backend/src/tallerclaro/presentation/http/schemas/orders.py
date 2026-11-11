"""Esquemas Pydantic para pedidos."""

from datetime import date

from pydantic import BaseModel, ConfigDict


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
    customer_name: str | None = None
    customer_email: str | None = None
    project_request: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OrderListResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    limit: int
    offset: int


class UpdateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

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
    customer_name: str | None = None
    customer_email: str | None = None
    project_request: str | None = None
