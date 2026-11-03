"""Router HTTP para pedidos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from tallerclaro.application.dtos import AccessPrincipal, UpdateOrderInput
from tallerclaro.application.use_cases import GetOrder, ListOrders, UpdateOrder
from tallerclaro.domain.entities import CarpenterId, OrderId
from tallerclaro.presentation.http.dependencies import (
    PrincipalDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
    get_unit_of_work,
    require_quote_or_workshop_principal,
    require_workshop_credentials,
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
        balance_amount=float(order.balance_amount.amount),
        currency=order.currency,
        status=order.status,
        estimated_delivery_date=order.estimated_delivery_date,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
    )


@router.get("/orders")
def list_orders(
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OrderListResponse:
    carpenter_id = (
        principal.carpenter_id
        if isinstance(principal, AccessPrincipal) and principal.carpenter_id is not None
        else CarpenterId(principal)
    )
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
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
) -> OrderDetailResponse:
    use_case = GetOrder(uow)
    detail = use_case.execute(OrderId(order_id), principal)
    order = detail.order
    payments = detail.payments
    return OrderDetailResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.balance_amount.amount),
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
        paid_amount=float(detail.paid_amount.amount),
        remaining_balance=float(detail.remaining_balance.amount),
        customer_name=detail.customer_name,
        customer_email=detail.customer_email,
        project_request=detail.project_request,
    )


@router.patch("/orders/{order_id}")
def update_order(
    order_id: int,
    body: UpdateOrderRequest,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
) -> OrderResponse:
    carpenter_id = (
        principal.carpenter_id
        if isinstance(principal, AccessPrincipal) and principal.carpenter_id is not None
        else CarpenterId(principal)
    )
    use_case = UpdateOrder(uow)
    order = use_case.execute(
        OrderId(order_id),
        carpenter_id,
        UpdateOrderInput(
            status=body.status,
            estimated_delivery_date=body.estimated_delivery_date,
        ),
    )
    return _to_order_response(order)
