"""Esquemas Pydantic para pagos."""

from pydantic import BaseModel, ConfigDict


class CreatePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: str  # deposit | balance


class PaymentIntentResponse(BaseModel):
    payment_id: str
    paypal_order_id: str
    amount: float
    currency: str
    approval_url: str | None = None


class PaymentResponse(BaseModel):
    id: str
    order_id: str
    type: str
    amount: float
    currency: str
    status: str
    paypal_order_id: str | None
    paypal_capture_id: str | None
    created_at: str | None = None
    paid_at: str | None = None


class CapturePaymentResponse(BaseModel):
    payment_id: str
    status: str
    paypal_order_id: str
    paypal_capture_id: str
    amount: float
    currency: str
    paid_at: str
