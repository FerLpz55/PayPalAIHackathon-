"""Dobles de repositorios y servicios para pruebas."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from decimal import Decimal

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    QuoteLineItemInput,
    QuoteProposalResult,
)
from tallerclaro.application.interfaces import AIService, PaymentProcessor, UnitOfWork
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
    def __init__(self) -> None:
        self._store: dict[QuoteId, Quote] = {}
        self._next_id = 1
        self._next_line_item_id = 1

    def save(self, quote: Quote) -> Quote:
        if quote.id is None:
            quote.id = QuoteId(self._next_id)
            self._next_id += 1
        persisted_items = []
        for item in quote.line_items:
            if item.id is None:
                item = replace(item, id=self._next_line_item_id)
                self._next_line_item_id += 1
            else:
                self._next_line_item_id = max(self._next_line_item_id, item.id + 1)
            persisted_items.append(item)
        quote.line_items = persisted_items
        quote.created_at = quote.created_at or datetime.now(timezone.utc)
        quote.updated_at = datetime.now(timezone.utc)
        self._store[quote.id] = quote
        return quote

    def get_by_id(self, quote_id: QuoteId) -> Quote | None:
        return self._store.get(quote_id)


class FakeCaptureReservationRepository:
    """Reserva de captura en memoria con la misma semántica que PostgreSQL."""

    def __init__(self) -> None:
        self._captures: dict[OrderId, PaymentId] = {}

    def reserve(self, order_id: OrderId, payment_id: PaymentId) -> bool:
        current = self._captures.get(order_id)
        if current is not None and current != payment_id:
            return False
        self._captures[order_id] = payment_id
        return True

    def release(self, order_id: OrderId, payment_id: PaymentId) -> None:
        if self._captures.get(order_id) == payment_id:
            self._captures.pop(order_id)


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

    def list_by_order(self, order_id: OrderId) -> list[Payment]:
        return [p for p in self._store.values() if p.order_id == order_id]


class FakeCustomerTokenRepository:
    def __init__(self, ttl_hours: int = 72, *, clock: Callable[[], datetime] | None = None) -> None:
        self._tokens: dict[str, dict] = {}
        self._counter = 0
        self._ttl_hours = ttl_hours
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        self._counter += 1
        token = f"fake-token-{self._counter}"
        self._tokens[token] = {'customer_id': customer_id, 'quote_id': quote_id, 'expiration': self._clock() + timedelta(hours=self._ttl_hours), 'used': False}
        return token

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
        record = self._tokens.get(token)
        if record is None or record['used'] or record['expiration'] < self._clock():
            return None
        return record['customer_id'], record['quote_id']


class FakeUnitOfWork:
    """Unidad de trabajo en memoria para pruebas unitarias con soporte real de commit y rollback."""

    def __init__(self, *, tokens=None) -> None:
        self._customers = FakeCustomerRepository()
        self._carpenters = FakeCarpenterRepository()
        self._quotes = FakeQuoteRepository()
        self._orders = FakeOrderRepository()
        self._capture_reservations = FakeCaptureReservationRepository()
        self._payments = FakePaymentRepository()
        self._tokens = tokens if tokens is not None else FakeCustomerTokenRepository()
        self._committed = False
        self._frames: list[dict] = []

    def _active_frame(self):
        if not self._frames:
            raise RuntimeError("Transaction is not open")
        return self._frames[-1]

    @property
    def customers(self):
        self._active_frame()
        return self._customers

    @property
    def carpenters(self):
        self._active_frame()
        return self._carpenters

    @property
    def quotes(self):
        self._active_frame()
        return self._quotes

    @property
    def orders(self):
        self._active_frame()
        return self._orders

    @property
    def payments(self):
        self._active_frame()
        return self._payments

    @property
    def tokens(self):
        self._active_frame()
        return self._tokens

    @property
    def capture_reservations(self):
        self._active_frame()
        return self._capture_reservations

    def _take_snapshot(self) -> dict:
        return {
            "customers_store": copy.deepcopy(self._customers._store),
            "customers_next_id": self._customers._next_id,
            "carpenters_store": copy.deepcopy(self._carpenters._store),
            "carpenters_next_id": self._carpenters._next_id,
            "quotes_store": copy.deepcopy(self._quotes._store),
            "quotes_next_id": self._quotes._next_id,
            "quotes_next_line_item_id": self._quotes._next_line_item_id,
            "orders_store": copy.deepcopy(self._orders._store),
            "orders_next_id": self._orders._next_id,
            "capture_reservations": copy.deepcopy(self._capture_reservations._captures),
            "payments_store": copy.deepcopy(self._payments._store),
            "payments_next_id": self._payments._next_id,
            "tokens_dict": copy.deepcopy({key: value for key, value in self._tokens.__dict__.items() if key != '_clock'}),
        }

    def _restore_snapshot(self, snap: dict) -> None:
        self._customers._store = copy.deepcopy(snap["customers_store"])
        self._customers._next_id = snap["customers_next_id"]
        self._carpenters._store = copy.deepcopy(snap["carpenters_store"])
        self._carpenters._next_id = snap["carpenters_next_id"]
        self._quotes._store = copy.deepcopy(snap["quotes_store"])
        self._quotes._next_id = snap["quotes_next_id"]
        self._quotes._next_line_item_id = snap["quotes_next_line_item_id"]
        self._orders._store = copy.deepcopy(snap["orders_store"])
        self._orders._next_id = snap["orders_next_id"]
        self._capture_reservations._captures = copy.deepcopy(snap["capture_reservations"])
        self._payments._store = copy.deepcopy(snap["payments_store"])
        self._payments._next_id = snap["payments_next_id"]
        clock = self._tokens.__dict__.get('_clock')
        self._tokens.__dict__.clear()
        self._tokens.__dict__.update(copy.deepcopy(snap["tokens_dict"]))
        if clock is not None:
            self._tokens._clock = clock

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
        self._active_frame()
        self._committed = True
        if self._frames:
            self._frames[-1]["committed"] = True
            self._frames[-1]["snapshot"] = self._take_snapshot()

    def rollback(self) -> None:
        self._active_frame()
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
