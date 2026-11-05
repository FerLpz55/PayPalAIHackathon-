"""Dobles de repositorios y servicios para pruebas."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from decimal import Decimal

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    QuoteLineItemInput,
    QuoteProposalResult,
)
from tallerclaro.application.interfaces import AIService, PaymentProcessor, UnitOfWork
from tallerclaro.domain.accounting import WorkshopFinancialSummary
from tallerclaro.domain.entities import (
    Carpenter,
    CarpenterId,
    Customer,
    CustomerId,
    Money,
    Order,
    OrderId,
    Payment,
    PaymentId,
    Quote,
    QuoteId,
    QuoteLineItem,
)


class FakeCustomerRepository:
    def __init__(self) -> None:
        self._store: dict[CustomerId, Customer] = {}
        self._next_id = 1

    def save(self, customer: Customer) -> Customer:
        if customer.id is None:
            customer.id = CustomerId(self._next_id)
            self._next_id += 1
        customer.created_at = customer.created_at or datetime.now(timezone.utc)
        customer.updated_at = datetime.now(timezone.utc)
        self._store[customer.id] = customer
        return customer

    def get_by_id(self, customer_id: CustomerId) -> Customer | None:
        return self._store.get(customer_id)


class FakeCarpenterRepository:
    def __init__(self) -> None:
        self._store: dict[CarpenterId, Carpenter] = {}
        self._next_id = 1

    def seed(self, carpenter: Carpenter) -> Carpenter:
        if carpenter.id is None:
            carpenter.id = CarpenterId(self._next_id)
            self._next_id += 1
        self._store[carpenter.id] = carpenter
        return carpenter

    def get_by_id(self, carpenter_id: CarpenterId) -> Carpenter | None:
        return self._store.get(carpenter_id)


class FakeQuoteRepository:
    def __init__(self, customer_repo: FakeCustomerRepository | None = None) -> None:
        self._store: dict[QuoteId, Quote] = {}
        self._next_id = 1
        self._customer_repo = customer_repo

    def save(self, quote: Quote) -> Quote:
        if quote.id is None:
            quote.id = QuoteId(self._next_id)
            self._next_id += 1
        quote.created_at = quote.created_at or datetime.now(timezone.utc)
        quote.updated_at = datetime.now(timezone.utc)
        self._store[quote.id] = quote
        return quote

    def get_by_id(self, quote_id: QuoteId) -> Quote | None:
        return self._store.get(quote_id)

    def get_by_id_with_customer(self, quote_id: QuoteId) -> tuple[Quote, Customer] | None:
        quote = self._store.get(quote_id)
        if quote is None:
            return None
        if self._customer_repo is None:
            return None
        customer = self._customer_repo.get_by_id(quote.customer_id)
        if customer is None:
            return None
        return quote, customer


class FakeOrderRepository:
    def __init__(self) -> None:
        self._store: dict[OrderId, Order] = {}
        self._next_id = 1

    def save(self, order: Order) -> Order:
        if order.id is None:
            order.id = OrderId(self._next_id)
            self._next_id += 1
        order.created_at = order.created_at or datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)
        self._store[order.id] = order
        return order

    def get_by_id(self, order_id: OrderId) -> Order | None:
        return self._store.get(order_id)

    def get_by_quote_id(self, quote_id: QuoteId) -> Order | None:
        for order in self._store.values():
            if order.quote_id == quote_id:
                return order
        return None

    def list_by_carpenter(
        self, carpenter_id: CarpenterId, limit: int, offset: int
    ) -> list[Order]:
        items = [o for o in self._store.values() if o.carpenter_id == carpenter_id]
        items.sort(key=lambda o: o.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return items[offset : offset + limit]

    def count_by_carpenter(self, carpenter_id: CarpenterId) -> int:
        return sum(1 for o in self._store.values() if o.carpenter_id == carpenter_id)


class FakePaymentRepository:
    def __init__(self) -> None:
        self._store: dict[PaymentId, Payment] = {}
        self._next_id = 1

    def save(self, payment: Payment) -> Payment:
        if payment.id is None:
            payment.id = PaymentId(self._next_id)
            self._next_id += 1
        payment.created_at = payment.created_at or datetime.now(timezone.utc)
        payment.updated_at = datetime.now(timezone.utc)
        self._store[payment.id] = payment
        return payment

    def get_by_id(self, payment_id: PaymentId) -> Payment | None:
        return self._store.get(payment_id)

    def get_by_paypal_order_id(self, paypal_order_id: str) -> Payment | None:
        for payment in self._store.values():
            if payment.paypal_order_id == paypal_order_id:
                return payment
        return None

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        return [p for p in self._store.values() if p.order_id == order_id]


class FakeCustomerTokenRepository:
    def __init__(self) -> None:
        self._tokens: dict[str, tuple[CustomerId, QuoteId]] = {}
        self._counter = 0

    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        self._counter += 1
        token = f"fake-token-{self._counter}"
        self._tokens[token] = (customer_id, quote_id)
        return token

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
        return self._tokens.get(token)


class FakeUnitOfWork:
    """Unidad de trabajo en memoria para pruebas unitarias con soporte real de commit y rollback."""

    def __init__(self) -> None:
        self.customers = FakeCustomerRepository()
        self.carpenters = FakeCarpenterRepository()
        self.quotes = FakeQuoteRepository(self.customers)
        self.orders = FakeOrderRepository()
        self.payments = FakePaymentRepository()
        self.tokens = FakeCustomerTokenRepository()
        self._committed = False
        self._frames: list[dict] = []

    def _take_snapshot(self) -> dict:
        return {
            "customers_store": copy.deepcopy(self.customers._store),
            "customers_next_id": self.customers._next_id,
            "carpenters_store": copy.deepcopy(self.carpenters._store),
            "carpenters_next_id": self.carpenters._next_id,
            "quotes_store": copy.deepcopy(self.quotes._store),
            "quotes_next_id": self.quotes._next_id,
            "orders_store": copy.deepcopy(self.orders._store),
            "orders_next_id": self.orders._next_id,
            "payments_store": copy.deepcopy(self.payments._store),
            "payments_next_id": self.payments._next_id,
            "tokens_dict": copy.deepcopy(self.tokens.__dict__),
        }

    def _restore_snapshot(self, snap: dict) -> None:
        self.customers._store = copy.deepcopy(snap["customers_store"])
        self.customers._next_id = snap["customers_next_id"]
        self.carpenters._store = copy.deepcopy(snap["carpenters_store"])
        self.carpenters._next_id = snap["carpenters_next_id"]
        self.quotes._store = copy.deepcopy(snap["quotes_store"])
        self.quotes._next_id = snap["quotes_next_id"]
        self.orders._store = copy.deepcopy(snap["orders_store"])
        self.orders._next_id = snap["orders_next_id"]
        self.payments._store = copy.deepcopy(snap["payments_store"])
        self.payments._next_id = snap["payments_next_id"]
        self.tokens.__dict__.clear()
        self.tokens.__dict__.update(copy.deepcopy(snap["tokens_dict"]))

    def __enter__(self) -> UnitOfWork:
        self._frames.append(
            {
                "snapshot": self._take_snapshot(),
                "committed": False,
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._frames:
            return
        frame = self._frames.pop()
        if exc_type is not None or not frame["committed"]:
            self._restore_snapshot(frame["snapshot"])

    def commit(self) -> None:
        self._committed = True
        if self._frames:
            self._frames[-1]["committed"] = True
            self._frames[-1]["snapshot"] = self._take_snapshot()

    def rollback(self) -> None:
        self._committed = False
        if self._frames:
            self._restore_snapshot(self._frames[-1]["snapshot"])
            self._frames[-1]["committed"] = False

    def get_connection(self):
        raise RuntimeError("FakeUnitOfWork has no database connection")


class FakeDependenciesContainer:
    """Contenedor de dependencias de prueba."""

    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.ai = FakeAIService()
        self.payment = FakePaymentProcessor(success=True)
        self.accounting = FakeAccountingAssistant(self.uow)


class FakeAIService:
    """IA determinista para pruebas."""

    def __init__(self, proposal: QuoteProposalResult | None = None) -> None:
        self._proposal = proposal or QuoteProposalResult(
            description="Test proposal",
            line_items=[
                QuoteLineItemInput(
                    type="material",
                    description="Wood",
                    unit="piece",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                )
            ],
        )

    def generate_quote_proposal(self, request: str) -> QuoteProposalResult:
        return self._proposal


class FakePaymentProcessor:
    """Procesador de pagos determinista para pruebas."""

    def __init__(self, success: bool = True) -> None:
        self._success = success
        self._orders: dict[str, PaymentIntent] = {}
        self._counter = 0

    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        self._counter += 1
        paypal_order_id = f"PAYPAL-{self._counter}"
        intent = PaymentIntent(
            payment_id=PaymentId(0),
            paypal_order_id=paypal_order_id,
            amount=Decimal(amount),
            currency=currency,
            approval_url=f"https://sandbox.paypal.com/checkoutnow?token={paypal_order_id}",
        )
        self._orders[paypal_order_id] = intent
        return intent

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        if paypal_order_id not in self._orders:
            from tallerclaro.domain.exceptions import DomainError

            raise DomainError(code="PAYMENT_NOT_FOUND", message="Order not found")
        if not self._success:
            from tallerclaro.domain.exceptions import DomainError

            raise DomainError(code="PAYMENT_FAILED", message="Capture failed")
        intent = self._orders[paypal_order_id]
        return CapturedPayment(
            payment_id=PaymentId(0),
            status="completed",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=f"CAPTURE-{paypal_order_id}",
            amount=intent.amount,
            currency=intent.currency,
            paid_at=datetime.now(timezone.utc).isoformat(),
        )


class FakeAccountingAssistant:
    """Asistente contable determinista que registra lo que recibe."""

    def __init__(self, uow: FakeUnitOfWork | None = None, answer: str = "Your workshop is doing fine.") -> None:
        self._uow = uow
        self._answer = answer
        self.calls: list[tuple[WorkshopFinancialSummary, str]] = []
        self.open_transactions_at_call: list[int] = []

    def explain(self, summary: WorkshopFinancialSummary, question: str) -> str:
        self.calls.append((summary, question))
        if self._uow is not None:
            self.open_transactions_at_call.append(len(self._uow._frames))
        return self._answer
