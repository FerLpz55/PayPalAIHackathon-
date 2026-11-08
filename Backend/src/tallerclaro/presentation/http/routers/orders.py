"""Router HTTP para pedidos."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tallerclaro.application.dtos import AccessPrincipal, UpdateOrderInput
from tallerclaro.application.use_cases import GetOrder, ListOrders, UpdateOrder
from tallerclaro.domain.entities import CarpenterId, OrderId
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
    orders, total = ListOrders(uow).execute(carpenter_id, limit, offset)
    return OrderListResponse(
        orders=[_to_order_response(order) for order in orders],
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
