"""Router HTTP para pagos."""

from __future__ import annotations

from fastapi import APIRouter

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.use_cases import CapturePayment, CreateOrderPayment, GetPayment
from tallerclaro.domain.entities import OrderId, PaymentId
from tallerclaro.presentation.http.dependencies import (
    CustomerTokenDep,
    PaymentProcessorDep,
    UnitOfWorkDep,
)
from tallerclaro.presentation.http.mappers import to_payment_response as _to_payment_response
from tallerclaro.presentation.http.schemas.payments import (
    CapturePaymentResponse,
    CreatePaymentRequest,
    PaymentIntentResponse,
    PaymentResponse,
)

router = APIRouter(prefix="/api", tags=["payments"])


def _extract_quote_id(token_data: object) -> int | None:
    if isinstance(token_data, AccessPrincipal):
        return token_data.quote_id
    if isinstance(token_data, (tuple, list)) and len(token_data) > 1:
        return token_data[1]
    return getattr(token_data, "quote_id", None)


@router.post("/orders/{order_id}/payments")
def create_payment(
    order_id: int,
    body: CreatePaymentRequest,
    token_data: CustomerTokenDep,
    uow: UnitOfWorkDep,
    payment_processor: PaymentProcessorDep,
) -> PaymentIntentResponse:
    authorized_quote_id = _extract_quote_id(token_data)
    intent = CreateOrderPayment(uow, payment_processor).execute(
        OrderId(order_id),
        body.type,
        authorized_quote_id=authorized_quote_id,
    )
    return PaymentIntentResponse(
        payment_id=str(intent.payment_id),
        paypal_order_id=intent.paypal_order_id,
        amount=float(intent.amount),
        currency=intent.currency,
        approval_url=intent.approval_url,
    )


@router.post("/payments/{payment_id}/capture")
def capture_payment(
    payment_id: int,
    token_data: CustomerTokenDep,
    uow: UnitOfWorkDep,
    payment_processor: PaymentProcessorDep,
) -> CapturePaymentResponse:
    authorized_quote_id = _extract_quote_id(token_data)
    captured = CapturePayment(uow, payment_processor).execute(
        PaymentId(payment_id),
        authorized_quote_id=authorized_quote_id,
    )
    return CapturePaymentResponse(
        payment_id=str(captured.payment_id),
        status=captured.status,
        paypal_order_id=captured.paypal_order_id,
        paypal_capture_id=captured.paypal_capture_id,
        amount=float(captured.amount),
        currency=captured.currency,
        paid_at=captured.paid_at,
    )


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    token_data: CustomerTokenDep,
    uow: UnitOfWorkDep,
) -> PaymentResponse:
    authorized_quote_id = _extract_quote_id(token_data)
    payment = GetPayment(uow).execute(
        PaymentId(payment_id),
        authorized_quote_id=authorized_quote_id,
    )
    return _to_payment_response(payment)
