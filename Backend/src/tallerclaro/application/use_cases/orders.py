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
from tallerclaro.application.interfaces import UnitOfWork
from tallerclaro.application.use_cases.authorization import authorize_workshop_or_customer
from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_PAID,
    CarpenterId,
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

    def execute_with_context(
        self, carpenter_id: CarpenterId, limit: int = 20, offset: int = 0
    ) -> tuple[list[tuple[Order, str | None, str | None, str | None]], int]:
        with self._uow:
            orders = self._uow.orders.list_by_carpenter(carpenter_id, limit, offset)
            total = self._uow.orders.count_by_carpenter(carpenter_id)
            enriched: list[tuple[Order, str | None, str | None, str | None]] = []
            for order in orders:
                cust_name = None
                cust_email = None
                proj_req = None
                quote = self._uow.quotes.get_by_id(order.quote_id)
                if quote:
                    proj_req = quote.request
                    customer = self._uow.customers.get_by_id(quote.customer_id)
                    if customer:
                        cust_name = customer.name
                        cust_email = customer.email
                enriched.append((order, cust_name, cust_email, proj_req))
            return enriched, total


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

            authorize_workshop_or_customer(
                principal,
                carpenter_id=order.carpenter_id,
                quote_id=order.quote_id,
                resource_name="order",
            )
            return self._build_order_detail(order)

    def _build_order_detail(self, order: Order) -> OrderDetailResult:
        payments = self._uow.payments.list_by_order(order.id)
        quote = self._uow.quotes.get_by_id(order.quote_id)
        customer = self._uow.customers.get_by_id(quote.customer_id) if quote else None

        return OrderDetailResult(
            order=order,
            payments=payments,
            customer_name=customer.name if customer else None,
            customer_email=customer.email if customer else None,
            project_request=quote.request if quote else None,
            paid_amount=order.calculate_paid_amount(payments),
            remaining_balance=order.calculate_remaining_balance(payments),
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
        resolved_carpenter_id, update_input = self._resolve_update_arguments(carpenter_id, input)

        with self._uow:
            order = self._uow.orders.get_by_id(order_id)
            if order is None:
                raise NotFoundError("Order", order_id)
            if resolved_carpenter_id is not None and order.carpenter_id != resolved_carpenter_id:
                raise ForbiddenError("Not authorized to update this order")

            self._apply_updates(order, update_input)
            order = self._uow.orders.save(order)
            self._uow.commit()
            return order

    def _apply_updates(self, order: Order, update_input: UpdateOrderInput) -> None:
        if update_input.status is not None:
            if update_input.status == ORDER_STATUS_DELIVERED:
                self._ensure_order_can_be_delivered(order)
            order.update_status(update_input.status, update_input.estimated_delivery_date)
        elif update_input.estimated_delivery_date is not None:
            order.estimated_delivery_date = update_input.estimated_delivery_date

    def _ensure_order_can_be_delivered(self, order: Order) -> None:
        payments = self._uow.payments.list_by_order(order.id)
        if not order.is_fully_paid(payments):
            raise ConflictError("Cannot deliver order without full payment verified")

    @staticmethod
    def _resolve_update_arguments(
        carpenter_id: CarpenterId | UpdateOrderInput | None,
        input: UpdateOrderInput | None,
    ) -> tuple[CarpenterId | None, UpdateOrderInput]:
        """Normaliza los argumentos aceptando tanto `(order_id, UpdateOrderInput)` como `(order_id, carpenter_id, UpdateOrderInput)`."""
        if isinstance(carpenter_id, UpdateOrderInput) and input is None:
            return None, carpenter_id
        return carpenter_id, (input if input is not None else UpdateOrderInput())
