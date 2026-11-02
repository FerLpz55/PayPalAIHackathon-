"""Casos de uso para pedidos."""

from __future__ import annotations

from datetime import date

from tallerclaro.application.dtos import UpdateOrderInput
from tallerclaro.application.exceptions import ConflictError, NotFoundError, ValidationDomainError
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

    def execute(self, order_id: OrderId) -> Order:
        with self._uow:
            order = self._uow.orders.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)
            return order


class UpdateOrder:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, order_id: OrderId, input: UpdateOrderInput) -> Order:
        with self._uow:
            order = self._uow.orders.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)
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
