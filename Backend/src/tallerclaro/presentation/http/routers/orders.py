"""Router HTTP para pedidos."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tallerclaro.application.dtos import AccessPrincipal, UpdateOrderInput
from tallerclaro.application.use_cases import GetOrder, ListOrders, UpdateOrder
from tallerclaro.domain.entities import ORDER_STATUS_DELETED, CarpenterId, OrderId
from tallerclaro.presentation.http.dependencies import (
    PrincipalDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
)
from tallerclaro.presentation.http.mappers import (
    to_order_detail_response as _to_order_detail_response,
    to_order_response as _to_order_response,
)
from tallerclaro.presentation.http.schemas.orders import (
    OrderDetailResponse,
    OrderListResponse,
    OrderResponse,
    UpdateOrderRequest,
)

router = APIRouter(prefix="/api", tags=["orders"])


def _resolve_carpenter_id(principal: AccessPrincipal | int) -> CarpenterId:
    if isinstance(principal, AccessPrincipal) and principal.carpenter_id is not None:
        return principal.carpenter_id
    return CarpenterId(principal)


@router.get("/orders")
def list_orders(
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OrderListResponse:
    carpenter_id = _resolve_carpenter_id(principal)
    enriched_orders, total = ListOrders(uow).execute_with_context(carpenter_id, limit, offset)

    order_responses = [
        _to_order_response(
            order,
            customer_name=cust_name,
            customer_email=cust_email,
            project_request=proj_req,
        )
        for order, cust_name, cust_email, proj_req in enriched_orders
    ]

    return OrderListResponse(
        orders=order_responses,
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
    detail = GetOrder(uow).execute(OrderId(order_id), principal)
    return _to_order_detail_response(detail)


@router.patch("/orders/{order_id}")
def update_order(
    order_id: int,
    body: UpdateOrderRequest,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
) -> OrderResponse:
    carpenter_id = _resolve_carpenter_id(principal)
    order = UpdateOrder(uow).execute(
        OrderId(order_id),
        carpenter_id,
        UpdateOrderInput(
            status=body.status,
            estimated_delivery_date=body.estimated_delivery_date,
        ),
    )
    return _to_order_response(order)


@router.delete("/orders/{order_id}", include_in_schema=False)
def delete_order(
    order_id: int,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
) -> OrderResponse:
    carpenter_id = _resolve_carpenter_id(principal)
    order = UpdateOrder(uow).execute(
        OrderId(order_id),
        carpenter_id,
        UpdateOrderInput(status=ORDER_STATUS_DELETED),
    )
    return _to_order_response(order)
