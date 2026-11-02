"""Puertos (interfaces) de la capa de aplicación."""

from __future__ import annotations

from typing import Protocol

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    QuoteProposalResult,
)
from tallerclaro.domain.entities import (
    Carpenter,
    CarpenterId,
    Customer,
    CustomerId,
    Order,
    OrderId,
    Payment,
    PaymentId,
    Quote,
    QuoteId,
)


class CustomerRepository(Protocol):
    def save(self, customer: Customer) -> Customer:
        ...

    def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        ...


class CarpenterRepository(Protocol):
    def get_by_id(self, carpenter_id: CarpenterId) -> Carpenter | None:
        ...


class QuoteRepository(Protocol):
    def save(self, quote: Quote) -> Quote:
        ...

    def get_by_id(self, quote_id: QuoteId) -> Quote | None:
        ...

    def get_by_id_with_customer(self, quote_id: QuoteId) -> tuple[Quote, Customer] | None:
        ...


class OrderRepository(Protocol):
    def save(self, order: Order) -> Order:
        ...

    def get_by_id(self, order_id: OrderId) -> Order | None:
        ...

    def get_by_quote_id(self, quote_id: QuoteId) -> Order | None:
        ...

    def list_by_carpenter(
        self, carpenter_id: CarpenterId, limit: int, offset: int
    ) -> list[Order]:
        ...

    def count_by_carpenter(self, carpenter_id: CarpenterId) -> int:
        ...


class PaymentRepository(Protocol):
    def save(self, payment: Payment) -> Payment:
        ...

    def get_by_id(self, payment_id: PaymentId) -> Payment | None:
        ...

    def get_by_paypal_order_id(self, paypal_order_id: str) -> Payment | None:
        ...

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        ...


class UnitOfWork(Protocol):
    def __enter__(self) -> UnitOfWork:
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ...

    @property
    def customers(self) -> CustomerRepository:
        ...

    @property
    def carpenters(self) -> CarpenterRepository:
        ...

    @property
    def quotes(self) -> QuoteRepository:
        ...

    @property
    def orders(self) -> OrderRepository:
        ...

    @property
    def payments(self) -> PaymentRepository:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class AIService(Protocol):
    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        ...


class PaymentProcessor(Protocol):
    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        ...

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        ...
