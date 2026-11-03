"""Router HTTP para pagos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.use_cases import CapturePayment, CreateOrderPayment, GetPayment
from tallerclaro.domain.entities import OrderId, PaymentId
from tallerclaro.presentation.http.dependencies import (
    CustomerTokenDep,
    UnitOfWorkDep,
    get_unit_of_work,
    require_customer_token,
)
from tallerclaro.presentation.http.schemas.payments import (
    CapturePaymentResponse,
    CreatePaymentRequest,
    PaymentIntentResponse,
    PaymentResponse,
)

router = APIRouter(prefix="/api", tags=["payments"])


def _extract_quote_id(token_data) -> int | None:
    if isinstance(token_data, AccessPrincipal):
        return token_data.quote_id
    if isinstance(token_data, (tuple, list)) and len(token_data) > 1:
        return token_data[1]
    return getattr(token_data, "quote_id", None)


def _to_payment_response(payment) -> PaymentResponse:
    return PaymentResponse(
        id=str(payment.id),
        order_id=str(payment.order_id),
        type=payment.type,
        amount=float(payment.amount.amount),
        currency=payment.currency,
        status=payment.status,
        paypal_order_id=payment.paypal_order_id,
        paypal_capture_id=payment.paypal_capture_id,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
        paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
    )


@router.post("/orders/{order_id}/payments")
def create_payment(
    order_id: int,
    body: CreatePaymentRequest,
    request: Request,
    token_data: CustomerTokenDep,
    uow: UnitOfWorkDep,
) -> PaymentIntentResponse:
    payment_processor = request.app.state.payment_processor
    use_case = CreateOrderPayment(uow, payment_processor)
    authorized_quote_id = _extract_quote_id(token_data)
    intent = use_case.execute(
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
    request: Request,
    token_data: CustomerTokenDep,
    uow: UnitOfWorkDep,
) -> CapturePaymentResponse:
    payment_processor = request.app.state.payment_processor
    use_case = CapturePayment(uow, payment_processor)
    authorized_quote_id = _extract_quote_id(token_data)
    captured = use_case.execute(
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
    use_case = GetPayment(uow)
    authorized_quote_id = _extract_quote_id(token_data)
    payment = use_case.execute(
        PaymentId(payment_id),
        authorized_quote_id=authorized_quote_id,
    )
    return _to_payment_response(payment)
