"""Router HTTP para pedidos."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from tallerclaro.application.dtos import UpdateOrderInput
from tallerclaro.application.use_cases import GetOrder, ListOrders, UpdateOrder
from tallerclaro.domain.entities import CarpenterId, OrderId
from tallerclaro.presentation.http.dependencies import (
    require_workshop_credentials,
    get_unit_of_work,
)
from tallerclaro.presentation.http.schemas.orders import (
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    PaymentSummary,
    UpdateOrderRequest,
)

router = APIRouter(prefix="/api", tags=["orders"])


def _to_order_response(order) -> OrderResponse:
    return OrderResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.total.amount - order.deposit_amount.amount),
        currency=order.currency,
        status=order.status,
        estimated_delivery_date=order.estimated_delivery_date,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
    )


@router.get("/orders")
def list_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    carpenter_id: CarpenterId = Depends(require_workshop_credentials),
    uow=Depends(get_unit_of_work),
) -> OrderListResponse:
    use_case = ListOrders(uow)
    orders, total = use_case.execute(carpenter_id, limit, offset)
    return OrderListResponse(
        orders=[_to_order_response(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    carpenter_id: CarpenterId = Depends(require_workshop_credentials),
    uow=Depends(get_unit_of_work),
) -> OrderDetailResponse:
    use_case = GetOrder(uow)
    order = use_case.execute(OrderId(order_id))
    payments = uow.payments.list_by_order(order.id)
    paid = sum((p.amount.amount for p in payments if p.status == "completed"), Decimal("0"))
    return OrderDetailResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.total.amount - order.deposit_amount.amount),
        currency=order.currency,
        status=order.status,
        estimated_delivery_date=order.estimated_delivery_date,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
        payments=[
            PaymentSummary(
                id=str(p.id),
                type=p.type,
                amount=float(p.amount.amount),
                status=p.status,
                paypal_order_id=p.paypal_order_id,
            )
            for p in payments
        ],
        paid_amount=float(paid),
        remaining_balance=float(order.total.amount - paid),
    )


@router.patch("/orders/{order_id}")
def update_order(
    order_id: int,
    body: UpdateOrderRequest,
    carpenter_id: CarpenterId = Depends(require_workshop_credentials),
    uow=Depends(get_unit_of_work),
) -> OrderResponse:
    use_case = UpdateOrder(uow)
    order = use_case.execute(
        OrderId(order_id),
        UpdateOrderInput(
            status=body.status,
            estimated_delivery_date=body.estimated_delivery_date,
        ),
    )
    return _to_order_response(order)
