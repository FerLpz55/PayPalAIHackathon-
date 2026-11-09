"""Dobles de repositorios y servicios para pruebas."""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from collections.abc import Callable
from decimal import Decimal

from tallerclaro.application.dtos import (
    CapturedPayment,
    MarketPriceReference,
    PaymentIntent,
    ProviderOrder,
    QuoteLineItemInput,
    QuoteProposalResult,
    WebhookEvent,
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
    PaymentType,
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

    def active_payment_id(self, order_id: OrderId) -> PaymentId | None:
        return self._captures.get(order_id)


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
        items = [
            o
            for o in self._store.values()
            if o.carpenter_id == carpenter_id and o.status != "deleted"
        ]
        items.sort(key=lambda o: o.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return items[offset : offset + limit]

    def count_by_carpenter(self, carpenter_id: CarpenterId) -> int:
        return sum(
            1
            for o in self._store.values()
            if o.carpenter_id == carpenter_id and o.status != "deleted"
        )


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

    def get_by_paypal_order_id(self, paypal_order_id: str) -> Payment | None:
        for payment in self._store.values():
            if payment.paypal_order_id == paypal_order_id:
                return payment
        return None

    def list_stale_pending(self, updated_before: datetime, limit: int) -> list[Payment]:
        stale = [
            payment
            for payment in self._store.values()
            if payment.status == "pending"
            and payment.paypal_order_id is not None
            and (payment.updated_at or datetime.min.replace(tzinfo=timezone.utc))
            < updated_before
        ]
        stale.sort(key=lambda payment: payment.updated_at or datetime.min.replace(tzinfo=timezone.utc))
        return stale[:limit]

    def get_pending_by_order_and_type(
        self, order_id: OrderId, payment_type: PaymentType
    ) -> Payment | None:
        pending = [
            payment
            for payment in self._store.values()
            if payment.order_id == order_id
            and payment.type == payment_type
            and payment.status == "pending"
        ]
        if not pending:
            return None
        pending.sort(
            key=lambda payment: payment.created_at
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return pending[0]


class FakePayPalEventRepository:
    """Deduplicación de eventos con la misma semántica que PostgreSQL."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}
        self._details: dict[str, str | None] = {}

    def claim(self, event: WebhookEvent) -> str:
        state = self._states.get(event.id)
        if state is None:
            self._states[event.id] = "received"
            return "new"
        if state == "failed":
            self._states[event.id] = "received"
            self._details.pop(event.id, None)
            return "retry"
        return "duplicate"

    def mark_processed(
        self, event_id: str, outcome: str, detail: str | None = None
    ) -> None:
        self._states[event_id] = outcome
        self._details[event_id] = detail

    def state(self, event_id: str) -> str | None:
        return self._states.get(event_id)

    def detail(self, event_id: str) -> str | None:
        return self._details.get(event_id)


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

    def revoke_for_quote(self, quote_id: QuoteId) -> int:
        revoked = 0
        for record in self._tokens.values():
            if record['quote_id'] == quote_id and not record['used']:
                record['used'] = True
                revoked += 1
        return revoked


class FakeRateLimiter:
    """Contadores en memoria con la misma semántica que PostgreSQL."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, int], int] = {}

    @staticmethod
    def _start(now: datetime, window_seconds: int) -> int:
        epoch = int(now.timestamp())
        return epoch - (epoch % window_seconds)

    def retry_after(
        self, key: str, *, limit: int, window_seconds: int, now: datetime
    ) -> int | None:
        start = self._start(now, window_seconds)
        if self._counters.get((key, start), 0) < limit:
            return None
        expires = datetime.fromtimestamp(start + window_seconds, tz=timezone.utc)
        return max(1, int((expires - now).total_seconds()))

    def hit(self, key: str, *, window_seconds: int, now: datetime) -> int:
        start = self._start(now, window_seconds)
        value = self._counters.get((key, start), 0) + 1
        self._counters[(key, start)] = value
        return value

    def reset(self, key: str, *, window_seconds: int, now: datetime) -> None:
        self._counters[(key, self._start(now, window_seconds))] = 0


class FakeWorkshopSessionRepository:
    """Sesiones en memoria con la misma semántica que PostgreSQL.

    Guarda solo el SHA-256 del token; expone ``stored_hashes`` para comprobar que
    el valor en claro nunca se persiste.
    """

    def __init__(
        self,
        *,
        idle_minutes: int = 30,
        absolute_hours: int = 8,
        credential_fingerprint: str = "test-fingerprint",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions: dict[str, dict] = {}
        self._idle_minutes = idle_minutes
        self._absolute_hours = absolute_hours
        self._credential_fingerprint = credential_fingerprint
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    @property
    def stored_hashes(self) -> list[str]:
        return list(self._sessions)

    @staticmethod
    def _hash(token: str) -> str:
        import hashlib

        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(self, carpenter_id: CarpenterId) -> str:
        import secrets

        token = secrets.token_urlsafe(32)
        now = self._clock()
        self._sessions[self._hash(token)] = {
            "carpenter_id": carpenter_id,
            "fingerprint": self._credential_fingerprint,
            "expires": now + timedelta(hours=self._absolute_hours),
            "last_used": now,
            "revoked": False,
        }
        return token

    def verify(self, token: str) -> CarpenterId | None:
        record = self._sessions.get(self._hash(token))
        if record is None or record["revoked"]:
            return None
        if record["fingerprint"] != self._credential_fingerprint:
            return None
        now = self._clock()
        if record["expires"] <= now:
            return None
        if record["last_used"] <= now - timedelta(minutes=self._idle_minutes):
            return None
        record["last_used"] = now
        return record["carpenter_id"]

    def revoke(self, token: str) -> bool:
        record = self._sessions.get(self._hash(token))
        if record is None or record["revoked"]:
            return False
        record["revoked"] = True
        return True

    def revoke_all(self, carpenter_id: CarpenterId) -> int:
        revoked = 0
        for record in self._sessions.values():
            if record["carpenter_id"] == carpenter_id and not record["revoked"]:
                record["revoked"] = True
                revoked += 1
        return revoked


class FakeUnitOfWork:
    """Unidad de trabajo en memoria para pruebas unitarias con soporte real de commit y rollback."""

    def __init__(
        self,
        *,
        tokens=None,
        sessions=None,
        session_clock: Callable[[], datetime] | None = None,
        session_idle_minutes: int = 30,
        session_absolute_hours: int = 8,
        session_credential_fingerprint: str = "test-fingerprint",
    ) -> None:
        self._customers = FakeCustomerRepository()
        self._carpenters = FakeCarpenterRepository()
        self._quotes = FakeQuoteRepository()
        self._orders = FakeOrderRepository()
        self._capture_reservations = FakeCaptureReservationRepository()
        self._payments = FakePaymentRepository()
        self._tokens = tokens if tokens is not None else FakeCustomerTokenRepository()
        self._rate_limits = FakeRateLimiter()
        self._paypal_events = FakePayPalEventRepository()
        self._sessions = (
            sessions
            if sessions is not None
            else FakeWorkshopSessionRepository(
                idle_minutes=session_idle_minutes,
                absolute_hours=session_absolute_hours,
                credential_fingerprint=session_credential_fingerprint,
                clock=session_clock,
            )
        )
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
    def sessions(self):
        self._active_frame()
        return self._sessions

    @property
    def rate_limits(self):
        self._active_frame()
        return self._rate_limits

    @property
    def capture_reservations(self):
        self._active_frame()
        return self._capture_reservations

    @property
    def paypal_events(self):
        self._active_frame()
        return self._paypal_events

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
            "sessions_store": copy.deepcopy(self._sessions._sessions),
            "rate_limits": copy.deepcopy(self._rate_limits._counters),
            "paypal_events": copy.deepcopy(self._paypal_events._states),
            "paypal_event_details": copy.deepcopy(self._paypal_events._details),
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
        self._sessions._sessions = copy.deepcopy(snap["sessions_store"])
        self._rate_limits._counters = copy.deepcopy(snap["rate_limits"])
        self._paypal_events._states = copy.deepcopy(snap["paypal_events"])
        self._paypal_events._details = copy.deepcopy(snap["paypal_event_details"])
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

    def execute_sql(self, operation, *, attempts: int = 3):
        """Ejecuta la fase en el fake; no hay conflictos de serialización que reintentar."""
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        with self:
            result = operation(self)
            self.commit()
        return result


class FakeWebhookVerifier:
    """Verificador determinista: devuelve eventos encolados y registra llamadas."""

    def __init__(self) -> None:
        self.events: list[WebhookEvent] = []
        self.calls: list[tuple[dict[str, str], bytes]] = []
        self.error: Exception | None = None

    def queue(self, event: WebhookEvent) -> None:
        self.events.append(event)

    def verify(self, headers: dict[str, str], body: bytes) -> WebhookEvent:
        from tallerclaro.domain.exceptions import DomainError

        self.calls.append((dict(headers), body))
        if self.error is not None:
            raise self.error
        if not self.events:
            raise DomainError(
                code="UNAUTHORIZED",
                message="No verified event queued",
            )
        return self.events.pop(0)


class FakeDependenciesContainer:
    """Contenedor de dependencias de prueba."""

    def __init__(self) -> None:
        self.uow = FakeUnitOfWork()
        self.ai = FakeAIService()
        self.payment = FakePaymentProcessor(success=True)
        self.accounting = FakeAccountingAssistant(self.uow)
        self.webhook = FakeWebhookVerifier()


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
        self._request_ids: dict[str, PaymentIntent] = {}
        self._statuses: dict[str, str] = {}
        self._captures: dict[str, CapturedPayment] = {}
        self._counter = 0
        self.create_calls: list[str | None] = []
        self.capture_calls: list[str] = []

    def create_order(
        self, amount: str, currency: str, request_id: str | None = None
    ) -> PaymentIntent:
        self.create_calls.append(request_id)
        if request_id is not None and request_id in self._request_ids:
            # PayPal devuelve la misma orden para el mismo PayPal-Request-Id.
            return self._request_ids[request_id]
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
        self._statuses[paypal_order_id] = "CREATED"
        if request_id is not None:
            self._request_ids[request_id] = intent
        return intent

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        self.capture_calls.append(paypal_order_id)
        if paypal_order_id not in self._orders:
            from tallerclaro.domain.exceptions import DomainError

            raise DomainError(code="PAYMENT_NOT_FOUND", message="Order not found")
        if not self._success:
            from tallerclaro.domain.exceptions import DomainError

            raise DomainError(code="PAYMENT_FAILED", message="Capture failed")
        existing = self._captures.get(paypal_order_id)
        if existing is not None:
            return existing
        intent = self._orders[paypal_order_id]
        captured = CapturedPayment(
            payment_id=PaymentId(0),
            status="completed",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=f"CAPTURE-{paypal_order_id}",
            amount=intent.amount,
            currency=intent.currency,
            paid_at=datetime.now(timezone.utc).isoformat(),
        )
        self._captures[paypal_order_id] = captured
        self._statuses[paypal_order_id] = "COMPLETED"
        return captured

    def get_order(self, paypal_order_id: str) -> ProviderOrder:
        if paypal_order_id not in self._orders:
            from tallerclaro.domain.exceptions import DomainError

            raise DomainError(code="PAYMENT_NOT_FOUND", message="Order not found")
        status = self._statuses.get(paypal_order_id, "CREATED")
        return ProviderOrder(
            paypal_order_id=paypal_order_id,
            status=status,
            approval_url=self._orders[paypal_order_id].approval_url,
            capture=self._captures.get(paypal_order_id) if status == "COMPLETED" else None,
        )

    def set_order_status(self, paypal_order_id: str, status: str) -> None:
        """Fija el estado que devolverá ``get_order`` (para pruebas de sync)."""
        self._statuses[paypal_order_id] = status

    def mark_completed_externally(self, paypal_order_id: str) -> CapturedPayment:
        """Simula una captura completada fuera del backend (webhook o panel)."""
        intent = self._orders[paypal_order_id]
        captured = CapturedPayment(
            payment_id=PaymentId(0),
            status="completed",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=f"CAPTURE-{paypal_order_id}",
            amount=intent.amount,
            currency=intent.currency,
            paid_at=datetime.now(timezone.utc).isoformat(),
        )
        self._captures[paypal_order_id] = captured
        self._statuses[paypal_order_id] = "COMPLETED"
        return captured


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


class FakePriceLookupService:
    """Buscador de precios determinista para pruebas."""

    def __init__(self, references: list[MarketPriceReference] | None = None) -> None:
        self.references = references or []
        self.calls: list[str] = []

    def lookup_prices(self, request: str) -> list[MarketPriceReference]:
        self.calls.append(request)
        return list(self.references)
