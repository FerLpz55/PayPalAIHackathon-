"""Contratos e interfaces de la capa de aplicación.

Define las abstracciones (Protocols) que la capa de aplicación requiere
para interactuar con la persistencia, servicios de IA y procesadores de pago.
"""

from __future__ import annotations

from typing import Protocol

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    QuoteProposalResult,
)
from tallerclaro.domain.accounting import WorkshopFinancialSummary
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


class CustomerTokenRepository(Protocol):
    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        ...

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
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

    @property
    def tokens(self) -> CustomerTokenRepository:
        ...

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...


class AIService(Protocol):
    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        ...


class AccountingAssistant(Protocol):
    """Explica en lenguaje simple un resumen financiero ya calculado.

    Recibe solo totales agregados (sin datos personales de clientes) y nunca
    calcula importes: las cifras llegan resueltas desde el dominio.
    """

    def explain(self, summary: WorkshopFinancialSummary, question: str) -> str:
        ...


class PaymentProcessor(Protocol):
    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        ...

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        ...

