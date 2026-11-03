"""Casos de uso para pedidos."""

from __future__ import annotations

from datetime import date

from tallerclaro.application.dtos import (
    AccessPrincipal,
    OrderDetailResult,
    UpdateOrderInput,
)
from tallerclaro.application.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from tallerclaro.application.ports import UnitOfWork
from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PAID,
    CarpenterId,
    Money,
    Order,
    OrderId,
)


class ListOrders:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self, carpenter_id: CarpenterId, limit: int = 20, offset: int = 0
    ) -> tuple[list[Order], int]:
        with self._uow:
            orders = self._uow.orders.list_by_carpenter(carpenter_id, limit, offset)
            total = self._uow.orders.count_by_carpenter(carpenter_id)
            return orders, total


class GetOrder:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self, order_id: OrderId, principal: AccessPrincipal | None = None
    ) -> OrderDetailResult:
        with self._uow:
            order = self._uow.orders.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)

            if principal is not None:
                if principal.is_workshop:
                    if principal.carpenter_id is not None and order.carpenter_id != principal.carpenter_id:
                        raise ForbiddenError("Not authorized to access this order")
                elif principal.is_customer:
                    if principal.quote_id != order.quote_id:
                        raise ForbiddenError("Not authorized to access this order")
                else:
                    raise ForbiddenError("Invalid principal")

            payments = self._uow.payments.list_by_order(order.id)
            quote = self._uow.quotes.get_by_id(order.quote_id)
            customer = self._uow.customers.get_by_id(quote.customer_id) if quote else None

            return OrderDetailResult(
                order=order,
                payments=payments,
                customer_name=customer.name if customer else None,
                customer_email=customer.email if customer else None,
                project_request=quote.request if quote else None,
            )


class UpdateOrder:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        order_id: OrderId,
        carpenter_id: CarpenterId | UpdateOrderInput | None = None,
        input: UpdateOrderInput | None = None,
    ) -> Order:
        if isinstance(carpenter_id, UpdateOrderInput) and input is None:
            input = carpenter_id
            carpenter_id = None
        if input is None:
            input = UpdateOrderInput()

        with self._uow:
            order = self._uow.orders.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)
            if carpenter_id is not None and order.carpenter_id != carpenter_id:
                raise ForbiddenError("Not authorized to update this order")
            if input.status is not None:
                if input.status == ORDER_STATUS_DELIVERED:
                    payments = self._uow.payments.list_by_order(order_id)
                    paid = sum(
                        (p.amount.amount for p in payments if p.status == "completed"),
                        Money.zero().amount,
                    )
                    if paid < order.total.amount:
                        raise ConflictError("Cannot deliver order without full payment verified")
                order.update_status(input.status, input.estimated_delivery_date)
            elif input.estimated_delivery_date is not None:
                order.estimated_delivery_date = input.estimated_delivery_date
            order = self._uow.orders.save(order)
            self._uow.commit()
            return order


