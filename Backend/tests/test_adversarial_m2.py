"""Adversarial stress tests and empirical verification for Milestone 2.

Covers:
1. PostgresQuoteRepository: Zero-DELETE invariant, SQL operation logging,
   UPDATE on existing IDs, slot reuse, and INSERT on additions.
2. Resource-level IDOR matrix across all HTTP endpoints (/api/quotes/*, /api/orders/*, /api/payments/*).
3. Closed-connection simulation on GET /api/orders/{order_id} (lifecycle, payments & customer details).
4. Multi-origin CORS verification (preflight OPTIONS, headers, allowed vs rejected origins).
5. Auth boundary conditions: header tampering, empty tokens, expired tokens, forged HTTP Basic headers, whitespace credentials.
6. Pydantic schema validation: extra fields rejected with 422 (extra="forbid"), whitespace stripping.
7. Starlette deprecation warnings: ensure zero deprecation warnings occur in application code or exception handlers.
8. OpenAIAIService: network failure handling (token masking, traceback suppression) and item validation (negative qty, zero qty, non-numeric, invalid type, empty desc, negative price, zero price).
9. Cross-role authorization boundary: customer cannot access workshop endpoints; workshop cannot access customer payment endpoints.
"""

from __future__ import annotations

import base64
from decimal import Decimal
import json
import traceback
from unittest.mock import MagicMock
import warnings
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
import httpx
from starlette.exceptions import StarletteDeprecationWarning

from tallerclaro.application.dtos import (
    AccessPrincipal,
    CreatedQuoteResult,
    CreateQuoteInput,
    CustomerInput,
    QuoteLineItemInput,
    QuoteProposalResult,
    UpdateOrderInput,
)
from tallerclaro.application.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from tallerclaro.application.interfaces import UnitOfWork
from tallerclaro.bootstrap.settings import Settings
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
    QuoteLineItemId,
)
from tallerclaro.infrastructure.ai.service import OpenAIAIService
from tallerclaro.infrastructure.db.repositories import PostgresQuoteRepository
from tallerclaro.presentation.http import exception_handlers
from tallerclaro.presentation.http.dependencies import get_unit_of_work
from tests.fakes import (
    FakeAIService,
    FakeCustomerTokenRepository,
    FakePaymentProcessor,
    FakeUnitOfWork,
)


# ==============================================================================
# 1. POSTGRES QUOTE REPOSITORY: ZERO-DELETE & SQL OPERATION LOGGING VERIFICATION
# ==============================================================================

class SQLLoggingConnection:
    """Mock connection that records all executed SQL queries and parameters."""

    def __init__(self, existing_item_ids: list[int] | None = None):
        self.executed_queries: list[tuple[str, tuple]] = []
        self._existing_item_ids = list(existing_item_ids) if existing_item_ids is not None else []
        self._next_item_id = 900

    def execute(self, sql: str, params: tuple = ()):
        clean_sql = " ".join(sql.strip().split())
        self.executed_queries.append((clean_sql, params))

        mock_cursor = MagicMock()
        # INSERT or UPDATE cotizacion RETURNING id_cotizacion, fecha_creacion, ultima_actualizacion
        if "tallerclaro.cotizacion" in clean_sql:
            quote_id = params[-1] if "WHERE id_cotizacion = %s" in clean_sql else 42
            mock_cursor.fetchone.return_value = (quote_id, None, None)
            return mock_cursor

        # SELECT id_detalle FROM tallerclaro.detalle_cotizacion WHERE id_cotizacion = %s
        if "SELECT id_detalle FROM tallerclaro.detalle_cotizacion" in clean_sql:
            mock_cursor.fetchall.return_value = [(id_,) for id_ in self._existing_item_ids]
            return mock_cursor

        # INSERT INTO tallerclaro.detalle_cotizacion ... RETURNING id_detalle
        if "INSERT INTO tallerclaro.detalle_cotizacion" in clean_sql:
            new_id = self._next_item_id
            self._next_item_id += 1
            mock_cursor.fetchone.return_value = (new_id,)
            return mock_cursor

        # UPDATE tallerclaro.detalle_cotizacion
        if "UPDATE tallerclaro.detalle_cotizacion" in clean_sql:
            mock_cursor.fetchone.return_value = None
            return mock_cursor

        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        return mock_cursor


def test_quote_repo_save_never_executes_delete_when_items_shrink():
    """Verify that when a quote has fewer items than in DB, no DELETE query is ever issued."""
    mock_conn = SQLLoggingConnection(existing_item_ids=[101, 102, 103, 104])
    repo = PostgresQuoteRepository(mock_conn)

    quote = Quote(
        id=QuoteId(42),
        customer_id=CustomerId(1),
        carpenter_id=CarpenterId(1),
        request="Mesa chica",
        description="Mesa con menos partidas",
        line_items=[
            QuoteLineItem(
                id=QuoteLineItemId(101),
                type="material",
                description="Madera pino",
                unit="m2",
                quantity=Decimal("2"),
                unit_price=Money(Decimal("30")),
            ),
            QuoteLineItem(
                id=None,  # Should reuse next slot (102)
                type="labor",
                description="Armado",
                unit="hr",
                quantity=Decimal("4"),
                unit_price=Money(Decimal("25")),
            ),
        ],
        total=Money(Decimal("160")),
        status="pending_review",
    )

    saved_quote = repo.save(quote)

    for sql, _ in mock_conn.executed_queries:
        assert "DELETE" not in sql.upper(), f"Forbidden DELETE statement found: {sql}"

    assert saved_quote.line_items[0].id == 101
    assert saved_quote.line_items[1].id == 102

    active_updates = [q for q, _ in mock_conn.executed_queries if "activo = true" in q and q.startswith("UPDATE tallerclaro.detalle_cotizacion")]
    deactivate_updates = [q for q, _ in mock_conn.executed_queries if "activo = false" in q and q.startswith("UPDATE tallerclaro.detalle_cotizacion")]
    inserts = [q for q, _ in mock_conn.executed_queries if q.startswith("INSERT INTO tallerclaro.detalle_cotizacion")]
    deletes = [q for q, _ in mock_conn.executed_queries if "DELETE" in q.upper()]

    assert len(active_updates) == 2
    assert len(deactivate_updates) == 2
    assert len(inserts) == 0
    assert len(deletes) == 0


def test_quote_repo_save_inserts_when_items_expand_and_no_delete():
    """Verify that when a quote expands, it updates existing slots and inserts only the surplus, 0 DELETEs."""
    mock_conn = SQLLoggingConnection(existing_item_ids=[201])
    repo = PostgresQuoteRepository(mock_conn)

    quote = Quote(
        id=QuoteId(55),
        customer_id=CustomerId(2),
        carpenter_id=CarpenterId(1),
        request="Comedor grande",
        description="Comedor completo",
        line_items=[
            QuoteLineItem(
                id=QuoteLineItemId(201),
                type="material",
                description="Madera nogal",
                unit="m2",
                quantity=Decimal("5"),
                unit_price=Money(Decimal("80")),
            ),
            QuoteLineItem(
                id=None,  # Surplus 1 -> INSERT
                type="labor",
                description="Acabado poliuretano",
                unit="hr",
                quantity=Decimal("6"),
                unit_price=Money(Decimal("30")),
            ),
            QuoteLineItem(
                id=None,  # Surplus 2 -> INSERT
                type="other",
                description="Herrajes especiales",
                unit="juego",
                quantity=Decimal("2"),
                unit_price=Money(Decimal("45")),
            ),
        ],
        total=Money(Decimal("670")),
        status="pending_review",
    )

    saved_quote = repo.save(quote)

    for sql, _ in mock_conn.executed_queries:
        assert "DELETE" not in sql.upper()

    updates = [q for q, _ in mock_conn.executed_queries if q.startswith("UPDATE tallerclaro.detalle_cotizacion")]
    inserts = [q for q, _ in mock_conn.executed_queries if q.startswith("INSERT INTO tallerclaro.detalle_cotizacion")]
    deletes = [q for q, _ in mock_conn.executed_queries if "DELETE" in q.upper()]

    assert len(updates) == 1
    assert len(inserts) == 2
    assert len(deletes) == 0

    assert saved_quote.line_items[0].id == 201
    assert saved_quote.line_items[1].id == 900
    assert saved_quote.line_items[2].id == 901


def test_quote_repo_save_frozen_items_and_no_delete():
    """Verify frozen QuoteLineItem objects are updated without FrozenInstanceError and without DELETE."""
    mock_conn = SQLLoggingConnection(existing_item_ids=[201, 202])
    repo = PostgresQuoteRepository(mock_conn)

    item1 = QuoteLineItem(
        id=None,
        type="material",
        description="Cedro",
        unit="m2",
        quantity=Decimal("4"),
        unit_price=Money(Decimal("30")),
    )
    item2 = QuoteLineItem(
        id=None,
        type="labor",
        description="Lijado",
        unit="hr",
        quantity=Decimal("2"),
        unit_price=Money(Decimal("20")),
    )

    quote = Quote(
        id=QuoteId(50),
        customer_id=CustomerId(1),
        carpenter_id=CarpenterId(1),
        request="Mesa",
        description="Mesa con acabado",
        line_items=[item1, item2],
    )

    saved_quote = repo.save(quote)
    assert saved_quote.line_items[0].id == QuoteLineItemId(201)
    assert saved_quote.line_items[1].id == QuoteLineItemId(202)

    for sql, _ in mock_conn.executed_queries:
        assert "DELETE" not in sql.upper()


# ==============================================================================
# 2. RESOURCE-LEVEL IDOR MATRIX TESTING ACROSS HTTP ENDPOINTS
# ==============================================================================

class ExpiringFakeCustomerTokenRepository:
    """Token repository that supports simulating expired tokens."""

    def __init__(self) -> None:
        self._tokens: dict[str, tuple[CustomerId, QuoteId, bool]] = {}
        self._counter = 0

    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        self._counter += 1
        token = f"adv-token-{self._counter}"
        self._tokens[token] = (customer_id, quote_id, False)
        return token

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
        if token not in self._tokens:
            return None
        customer_id, quote_id, expired = self._tokens[token]
        if expired:
            return None
        return customer_id, quote_id

    def expire(self, token: str) -> None:
        if token in self._tokens:
            customer_id, quote_id, _ = self._tokens[token]
            self._tokens[token] = (customer_id, quote_id, True)


@pytest.fixture
def adversarial_app():
    from tallerclaro.main import create_app

    settings = Settings(
        workshop_username="taller",
        workshop_password_hash=__import__("bcrypt").hashpw(b"demo-password", __import__("bcrypt").gensalt(rounds=4)).decode(),
        workshop_carpenter_id=1,
        cors_origins=["http://localhost:5173", "https://tallerclaro.com"],
        enable_workshop_basic_auth=True,
    )
    expiring_tokens = ExpiringFakeCustomerTokenRepository()
    uow = FakeUnitOfWork(tokens=expiring_tokens)

    with uow:
        uow.carpenters.seed(
            Carpenter(
                id=CarpenterId(1),
                name="José Carpintero",
                workshop_name="Taller José",
                email="jose@tallerclaro.com",
                phone=None,
            )
        )
        uow.commit()
    ai_service = FakeAIService()
    payment_processor = FakePaymentProcessor(success=True)

    app = create_app(
        settings=settings,
        ai_service=ai_service,
        payment_processor=payment_processor,
    )

    def override_uow():
        return uow

    app.dependency_overrides[get_unit_of_work] = override_uow
    return TestClient(app), uow, ai_service, payment_processor, expiring_tokens


def test_idor_comprehensive_matrix_across_all_endpoints(adversarial_app):
    """Exhaustively verify that Customer A cannot access or manipulate Customer B's resources across all endpoints."""
    client, uow, _, _, _ = adversarial_app

    # Create Customer A quote
    resp_a = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Alice", "email": "alice@example.com"},
            "carpenter_id": 1,
            "request": "Mueble de baño para Alice",
        },
    )
    assert resp_a.status_code == 201
    quote_a_id = resp_a.json()["id"]
    token_a = resp_a.json()["customer_token"]

    # Create Customer B quote
    resp_b = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Bob", "email": "bob@example.com"},
            "carpenter_id": 1,
            "request": "Cama para Bob",
        },
    )
    assert resp_b.status_code == 201
    quote_b_id = resp_b.json()["id"]
    token_b = resp_b.json()["customer_token"]

    # Workshop generates proposals
    client.post(f"/api/quotes/{quote_a_id}/generate", auth=("taller", "demo-password"))
    client.post(f"/api/quotes/{quote_b_id}/generate", auth=("taller", "demo-password"))

    # Both approve their own quotes
    order_a_id = client.post(
        f"/api/quotes/{quote_a_id}/approve",
        headers={"X-Customer-Token": token_a},
    ).json()["id"]

    order_b_id = client.post(
        f"/api/quotes/{quote_b_id}/approve",
        headers={"X-Customer-Token": token_b},
    ).json()["id"]

    # Bob creates a payment for Order B
    pay_b_id = client.post(
        f"/api/orders/{order_b_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_b},
    ).json()["payment_id"]

    # Alice creates a payment for Order A
    pay_a_id = client.post(
        f"/api/orders/{order_a_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_a},
    ).json()["payment_id"]

    # --- IDOR ATTACK MATRIX: Customer A attacks Customer B's resources ---

    # 1. GET /api/quotes/{quote_b_id} using token A -> 403
    res = client.get(f"/api/quotes/{quote_b_id}", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 2. POST /api/quotes/{quote_b_id}/approve using token A -> 403
    res = client.post(f"/api/quotes/{quote_b_id}/approve", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 3. POST /api/quotes/{quote_b_id}/reject using token A -> 403
    res = client.post(f"/api/quotes/{quote_b_id}/reject", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 4. GET /api/orders/{order_b_id} using token A -> 403
    res = client.get(f"/api/orders/{order_b_id}", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 5. POST /api/orders/{order_b_id}/payments using token A -> 403
    res = client.post(
        f"/api/orders/{order_b_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_a},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 6. POST /api/payments/{pay_b_id}/capture using token A -> 403
    res = client.post(f"/api/payments/{pay_b_id}/capture", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # 7. GET /api/payments/{pay_b_id} using token A -> 403
    res = client.get(f"/api/payments/{pay_b_id}", headers={"X-Customer-Token": token_a})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    # --- IDOR ATTACK MATRIX IN REVERSE: Customer B attacks Customer A ---
    res = client.get(f"/api/quotes/{quote_a_id}", headers={"X-Customer-Token": token_b})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    res = client.get(f"/api/orders/{order_a_id}", headers={"X-Customer-Token": token_b})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    res = client.post(
        f"/api/orders/{order_a_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token_b},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"

    res = client.get(f"/api/payments/{pay_a_id}", headers={"X-Customer-Token": token_b})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


# ==============================================================================
# 3. CLOSED-CONNECTION SIMULATION & CONNECTION EXHAUSTION
# ==============================================================================

class StrictlyClosedUnitOfWorkWrapper:
    """Wrapper that closes and invalidates the connection immediately upon context exit."""

    def __init__(self, inner_uow: UnitOfWork):
        self._inner = inner_uow
        self.is_active = False
        self.enter_count = 0
        self.exit_count = 0

    def __enter__(self):
        self.is_active = True
        self.enter_count += 1
        self._inner.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.is_active = False
        self.exit_count += 1
        self._inner.__exit__(exc_type, exc_val, exc_tb)

    def _check_open(self):
        if not self.is_active:
            raise RuntimeError("CRITICAL: Database connection is closed! Query attempted outside active transaction.")

    @property
    def customers(self):
        self._check_open()
        return self._inner.customers

    @property
    def carpenters(self):
        self._check_open()
        return self._inner.carpenters

    @property
    def quotes(self):
        self._check_open()
        return self._inner.quotes

    @property
    def orders(self):
        self._check_open()
        return self._inner.orders

    @property
    def capture_reservations(self):
        self._check_open()
        return self._inner.capture_reservations

    @property
    def payments(self):
        self._check_open()
        return self._inner.payments

    @property
    def tokens(self):
        self._check_open()
        return self._inner.tokens

    @property
    def sessions(self):
        self._check_open()
        return self._inner.sessions

    def commit(self):
        self._check_open()
        self._inner.commit()

    def rollback(self):
        self._check_open()
        self._inner.rollback()

    def execute_sql(self, operation, *, attempts: int = 3):
        with self:
            result = operation(self)
            self.commit()
        return result


def test_closed_connection_simulation_get_order_executes_cleanly(adversarial_app):
    """Verify GET /api/orders/{order_id} loads payments, customer, and quote inside the transaction."""
    client, inner_uow, _, _, _ = adversarial_app
    wrapper = StrictlyClosedUnitOfWorkWrapper(inner_uow)

    client.app.dependency_overrides[get_unit_of_work] = lambda: wrapper

    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Elena Torres", "email": "elena@example.com", "phone": "555-9876"},
            "carpenter_id": 1,
            "request": "Librero moderno empotrado",
        },
    )
    assert resp.status_code == 201
    quote_id = resp.json()["id"]
    token = resp.json()["customer_token"]

    gen_resp = client.post(f"/api/quotes/{quote_id}/generate", auth=("taller", "demo-password"))
    assert gen_resp.status_code == 200
    order_id = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    ).json()["id"]

    pay_id = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    ).json()["payment_id"]

    res = client.get(
        f"/api/orders/{order_id}",
        headers={"X-Customer-Token": token},
    )
    assert res.status_code == 200, f"Failed with {res.status_code}: {res.text}"
    data = res.json()

    assert data["id"] == order_id
    assert data["quote_id"] == quote_id
    assert data["customer_name"] == "Elena Torres"
    assert data["customer_email"] == "elena@example.com"
    assert data["project_request"] == "Librero moderno empotrado"
    assert len(data["payments"]) == 1
    assert data["payments"][0]["id"] == pay_id
    assert "paid_amount" in data
    assert "remaining_balance" in data

    assert not wrapper.is_active, "Connection must NOT remain active after request finishes"


def test_repeated_queries_do_not_exhaust_connections(adversarial_app):
    """Stress test simulating 30 sequential requests to confirm every request cleanly closes its transaction."""
    client, uow, _, _, _ = adversarial_app
    wrapper = StrictlyClosedUnitOfWorkWrapper(uow)
    client.app.dependency_overrides[get_unit_of_work] = lambda: wrapper

    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Test Exhaustion", "email": "test@example.com"},
            "carpenter_id": 1,
            "request": "Banco",
        },
    )
    assert resp.status_code == 201
    quote_id = resp.json()["id"]
    token = resp.json()["customer_token"]
    client.post(f"/api/quotes/{quote_id}/generate", auth=("taller", "demo-password"))
    order_id = client.post(f"/api/quotes/{quote_id}/approve", headers={"X-Customer-Token": token}).json()["id"]

    for _ in range(30):
        r = client.get(f"/api/orders/{order_id}", headers={"X-Customer-Token": token})
        assert r.status_code == 200
        assert not wrapper.is_active

    assert wrapper.enter_count == wrapper.exit_count


# ==============================================================================
# 4. MULTI-ORIGIN CORS VERIFICATION
# ==============================================================================

def test_multi_origin_cors_preflight_and_headers():
    """Verify CORS preflight (OPTIONS) and response headers across multiple allowed origins and rejected origin."""
    from tallerclaro.main import create_app

    settings = Settings(
        cors_origins=[
            "http://localhost:5173",
            "https://tallerclaro.com",
            "https://admin.tallerclaro.internal",
        ]
    )
    uow = FakeUnitOfWork()
    app = create_app(settings=settings, ai_service=FakeAIService(), payment_processor=FakePaymentProcessor())
    app.dependency_overrides[get_unit_of_work] = lambda: uow
    client = TestClient(app)

    allowed_origins = [
        "http://localhost:5173",
        "https://tallerclaro.com",
        "https://admin.tallerclaro.internal",
    ]

    for origin in allowed_origins:
        # Preflight OPTIONS request
        opts = client.options(
            "/api/quotes",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-Customer-Token, Content-Type",
            },
        )
        assert opts.status_code == 200
        assert opts.headers.get("access-control-allow-origin") == origin
        assert opts.headers.get("access-control-allow-credentials") == "true"
        allow_headers = opts.headers.get("access-control-allow-headers", "").lower()
        assert "x-customer-token" in allow_headers or "*" in allow_headers

        # Actual GET request with Origin
        res = client.get("/api/health", headers={"Origin": origin})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin

    # Disallowed Origin
    disallowed_origin = "https://malicious-phishing-site.com"
    opts_bad = client.options(
        "/api/quotes",
        headers={
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert opts_bad.headers.get("access-control-allow-origin") != disallowed_origin

    res_bad = client.get("/api/health", headers={"Origin": disallowed_origin})
    assert res_bad.headers.get("access-control-allow-origin") != disallowed_origin


def test_cors_origins_settings_parsing_formats():
    """Verify Settings parses comma-separated string, JSON string, and lists properly."""
    s1 = Settings(cors_origins="http://a.com, https://b.com ,http://c.com")
    assert s1.cors_origins == ["http://a.com", "https://b.com", "http://c.com"]

    s2 = Settings(cors_origins='["http://foo.com", "https://bar.com"]')
    assert s2.cors_origins == ["http://foo.com", "https://bar.com"]

    s3 = Settings(cors_origins=["http://direct.com"])
    assert s3.cors_origins == ["http://direct.com"]


# ==============================================================================
# 5. AUTH BOUNDARY CONDITIONS & TAMPERING
# ==============================================================================

def test_adversarial_auth_header_tampering_malformed_base64(adversarial_app):
    client, uow, _, _, _ = adversarial_app

    malformed_headers = [
        {"Authorization": "Basic ???"},
        {"Authorization": "Basic !!!==="},
        {"Authorization": "Basic "},
        {"Authorization": "Basic " + base64.b64encode(b"no_colon_here").decode("ascii")},
        {"Authorization": "Basic " + base64.b64encode(b"\xff\xfe\x00\x01").decode("ascii")},
    ]

    for headers in malformed_headers:
        resp = client.get("/api/orders", headers=headers)
        assert resp.status_code == 401, f"Expected 401 for header {headers}, got {resp.status_code}"
        assert "detail" in resp.json()

        resp_q = client.get("/api/quotes/1", headers=headers)
        assert resp_q.status_code == 401, f"Expected 401 for header {headers}, got {resp_q.status_code}"
        assert "detail" in resp_q.json()


def test_adversarial_auth_header_whitespace_and_forged_credentials(adversarial_app):
    client, uow, _, _, _ = adversarial_app

    tampered_creds = [
        (" taller", "demo-password"),
        ("taller ", "demo-password"),
        ("taller", " demo-password"),
        ("taller", "demo-password "),
        (" ", " "),
        ("", ""),
        ("taller", "WRONG-PASSWORD"),
        ("ADMIN", "demo-password"),
    ]

    for user, pwd in tampered_creds:
        resp = client.get("/api/orders", auth=(user, pwd))
        assert resp.status_code == 401, f"Expected 401 for auth ({user}, {pwd}), got {resp.status_code}"
        assert "detail" in resp.json()


def test_adversarial_auth_empty_and_tampered_customer_tokens(adversarial_app):
    client, uow, _, _, expiring_tokens = adversarial_app

    res = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Alice", "email": "alice@example.com"},
            "carpenter_id": 1,
            "request": "Mesa",
        },
    )
    assert res.status_code == 201
    quote_id = res.json()["id"]
    valid_token = res.json()["customer_token"]

    tampered_tokens = [
        "",
        "   ",
        "invalid-token",
        valid_token + "_tampered",
        valid_token[:-1],
        "Bearer",
        "null",
        "0",
    ]

    for token in tampered_tokens:
        resp = client.get(f"/api/quotes/{quote_id}", headers={"X-Customer-Token": token})
        assert resp.status_code == 401, f"Expected 401 for token '{token}', got {resp.status_code}"

        resp_b = client.get(f"/api/quotes/{quote_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp_b.status_code == 401, f"Expected 401 for Bearer '{token}', got {resp_b.status_code}"

    ok_header = client.get(f"/api/quotes/{quote_id}", headers={"X-Customer-Token": valid_token})
    assert ok_header.status_code == 200

    ok_bearer = client.get(f"/api/quotes/{quote_id}", headers={"Authorization": f"Bearer {valid_token}"})
    assert ok_bearer.status_code == 200


def test_adversarial_auth_expired_customer_token(adversarial_app):
    client, uow, _, _, expiring_tokens = adversarial_app

    res = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Bob", "email": "bob@example.com"},
            "carpenter_id": 1,
            "request": "Silla",
        },
    )
    quote_id = res.json()["id"]
    token = res.json()["customer_token"]

    assert client.get(f"/api/quotes/{quote_id}", headers={"X-Customer-Token": token}).status_code == 200

    expiring_tokens.expire(token)

    resp = client.get(f"/api/quotes/{quote_id}", headers={"X-Customer-Token": token})
    assert resp.status_code == 401
    assert "Invalid or expired customer token" in resp.json()["detail"]


def test_adversarial_auth_cross_role_access_boundaries(adversarial_app):
    client, uow, _, _, _ = adversarial_app

    res = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Charlie", "email": "charlie@example.com"},
            "carpenter_id": 1,
            "request": "Puerta",
        },
    )
    token = res.json()["customer_token"]

    # 1. Customer token CANNOT access workshop-only routes
    resp = client.get("/api/orders", headers={"X-Customer-Token": token})
    assert resp.status_code == 401
    assert "Workshop session required" in resp.json()["detail"]

    resp = client.post("/api/quotes/1/generate", headers={"X-Customer-Token": token})
    assert resp.status_code == 401
    assert "Workshop session required" in resp.json()["detail"]

    resp = client.patch("/api/orders/1", json={"status": "in_progress"}, headers={"X-Customer-Token": token})
    assert resp.status_code == 401
    assert "Workshop session required" in resp.json()["detail"]

    # 2. Workshop credentials CANNOT access customer payment routes
    resp = client.post("/api/orders/1/payments", json={"type": "deposit"}, auth=("taller", "demo-password"))
    assert resp.status_code == 401
    assert "Customer token required" in resp.json()["detail"]

    resp = client.post("/api/payments/1/capture", auth=("taller", "demo-password"))
    assert resp.status_code == 401
    assert "Customer token required" in resp.json()["detail"]

    resp = client.get("/api/payments/1", auth=("taller", "demo-password"))
    assert resp.status_code == 401
    assert "Customer token required" in resp.json()["detail"]


# ==============================================================================
# 6. PYDANTIC SCHEMA VALIDATION (extra="forbid") & WHITESPACE STRIPPING
# ==============================================================================

def test_adversarial_schema_extra_fields_rejection(adversarial_app):
    client, uow, _, _, _ = adversarial_app

    # 1. CreateQuoteRequest - extra fields top-level
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Dave", "email": "dave@example.com"},
            "carpenter_id": 1,
            "request": "Ropero",
            "malicious_injected_field": 12345,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert any("malicious_injected_field" in err["field"] for err in resp.json()["field_errors"])

    # 2. CustomerInput - extra fields nested
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Dave", "email": "dave@example.com", "role": "admin", "privileges": "all"},
            "carpenter_id": 1,
            "request": "Ropero",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"

    # 3. GenerateQuoteRequest - extra fields
    resp = client.post(
        "/api/quotes/1/generate",
        json={"additional_info": "More details", "extra_option": "override"},
        auth=("taller", "demo-password"),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"

    # 4. UpdateOrderRequest - extra fields
    resp = client.patch(
        "/api/orders/1",
        json={"status": "in_progress", "total": 999999},
        auth=("taller", "demo-password"),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"

    # 5. CreatePaymentRequest - extra fields
    resp = client.post(
        "/api/orders/1/payments",
        json={"type": "deposit", "fake_status": "completed"},
        headers={"X-Customer-Token": "some-token"},
    )
    assert resp.status_code in (401, 422)


def test_adversarial_schema_whitespace_stripping(adversarial_app):
    client, uow, _, _, _ = adversarial_app

    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "   Frank White   ", "email": "frank@example.com"},
            "carpenter_id": 1,
            "request": "   Mesa de noche con cajones   ",
        },
    )
    assert resp.status_code == 201
    quote = resp.json()
    assert quote["request"] == "Mesa de noche con cajones"


# ==============================================================================
# 7. STARLETTE DEPRECATION WARNINGS VERIFICATION
# ==============================================================================

def test_adversarial_zero_starlette_deprecation_warnings_in_tallerclaro():
    """Verify that no StarletteDeprecationWarning is emitted by application code."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")

        status_map = {
            "UNAUTHORIZED": exception_handlers._domain_error_to_status(DomainError(message="unauth", code="UNAUTHORIZED")),
            "FORBIDDEN": exception_handlers._domain_error_to_status(ForbiddenError("forbidden")),
            "NOT_FOUND": exception_handlers._domain_error_to_status(NotFoundError("Order", 1)),
            "CONFLICT": exception_handlers._domain_error_to_status(ConflictError("conflict")),
            "VALIDATION_ERROR": exception_handlers._domain_error_to_status(ValidationDomainError("invalid")),
            "AI_RESPONSE_INVALID": exception_handlers._domain_error_to_status(DomainError(message="invalid", code="AI_RESPONSE_INVALID")),
            "BAD_GATEWAY": exception_handlers._domain_error_to_status(DomainError(message="bad gateway", code="BAD_GATEWAY")),
            "SERVICE_UNAVAILABLE": exception_handlers._domain_error_to_status(DomainError(message="unavailable", code="SERVICE_UNAVAILABLE")),
        }

        assert status_map["UNAUTHORIZED"] == 401
        assert status_map["FORBIDDEN"] == 403
        assert status_map["NOT_FOUND"] == 404
        assert status_map["CONFLICT"] == 409
        assert status_map["VALIDATION_ERROR"] == 422
        assert status_map["AI_RESPONSE_INVALID"] == 422
        assert status_map["BAD_GATEWAY"] == 502
        assert status_map["SERVICE_UNAVAILABLE"] == 503

        req = MagicMock(spec=Request)
        json_resp = exception_handlers.domain_error_handler(req, ValidationDomainError("test invalid"))
        assert json_resp.status_code == 422

        app_warnings = [
            w for w in recorded
            if issubclass(w.category, StarletteDeprecationWarning)
            and "tallerclaro" in str(w.filename)
        ]
        assert len(app_warnings) == 0, f"Deprecation warnings detected in application code: {app_warnings}"


# ==============================================================================
# 8. OPENAI AI SERVICE RESILIENCE & STRICT VALIDATION
# ==============================================================================

def test_adversarial_openai_network_failure_masks_token_and_headers():
    secret = "sk-topsecret-sensitive-api-token-987654321"
    settings = Settings(
        ai_api_key=secret,
        ai_provider="openai",
        ai_base_url="https://api.openai.com/v1",
    )

    failures = [
        httpx.ConnectError("Connection refused to remote server"),
        httpx.TimeoutException("Read timeout after 60s"),
        RuntimeError(f"Raw socket failure with headers Authorization: Bearer {secret}"),
        Exception(f"Crash containing {secret} in memory buffer"),
    ]

    for failure in failures:
        mock_client = MagicMock()
        mock_client.post.side_effect = failure
        service = OpenAIAIService(settings=settings, client=mock_client)

        with pytest.raises(DomainError) as exc_info:
            service.generate_quote_proposal("Mesa de roble")

        err = exc_info.value
        assert err.code == "SERVICE_UNAVAILABLE"
        assert secret not in err.message
        assert secret not in str(err)
        assert err.__cause__ is None
        assert err.__suppress_context__ is True
        tb = "".join(traceback.format_exception(err))
        assert secret not in tb


def test_adversarial_openai_missing_api_key():
    settings = Settings(ai_api_key="", ai_provider="openai")
    service = OpenAIAIService(settings=settings, client=MagicMock())
    with pytest.raises(DomainError) as exc_info:
        service.generate_quote_proposal("Mesa")
    assert exc_info.value.code == "SERVICE_UNAVAILABLE"
    assert "AI API key is missing" in exc_info.value.message


def test_adversarial_openai_item_validation_boundary_conditions():
    settings = Settings(ai_api_key="sk-test", ai_provider="openai")
    service = OpenAIAIService(settings=settings, client=MagicMock())

    invalid_payloads = [
        "This is plain text, not JSON",
        "{broken json",
        "[]",
        "\"a string\"",
        "12345",
        '{"needs_information": false, "description": "mesa", "items": []}',
        '{"needs_information": false, "description": "mesa"}',
        '{"items": ["not a dict"]}',
        '{"items": [{"type": "gold", "description": "mesa", "quantity": 1, "unit_price": 50}]}',
        '{"items": [{"type": "MATERIAL", "description": "mesa", "quantity": 1, "unit_price": 50}]}',
        '{"items": [{"type": "", "description": "mesa", "quantity": 1, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "", "quantity": 1, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "   ", "quantity": 1, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": -1, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": -0.0001, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 0, "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": "0.0", "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": "NaN", "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": "Infinity", "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": "abc", "unit_price": 50}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 1, "unit_price": -0.01}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 1, "unit_price": -500}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 1, "unit_price": "NaN"}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 1, "unit_price": "Infinity"}]}',
        '{"items": [{"type": "material", "description": "madera", "quantity": 1, "unit_price": "invalid"}]}',
    ]

    for payload in invalid_payloads:
        with pytest.raises(DomainError) as exc_info:
            service._parse_proposal(payload)
        assert exc_info.value.code == "AI_RESPONSE_INVALID", f"Expected AI_RESPONSE_INVALID for: {payload}"

    valid_zero_price_payload = (
        '{"description": "Mesa con ensamble incluido", '
        '"items": ['
        '  {"type": "material", "description": "Tablón de pino", "quantity": 2, "unit_price": 45.50},'
        '  {"type": "labor", "description": "Ensamble bonificado", "quantity": 1, "unit_price": 0}'
        '], '
        '"assumptions": ["Incluye acabado mate"]}'
    )
    result = service._parse_proposal(valid_zero_price_payload)
    assert not result.needs_information
    assert len(result.line_items) == 2
    assert result.line_items[1].unit_price == Decimal("0")
    assert result.assumptions == ["Incluye acabado mate"]


def test_ai_proposal_parser_handles_markdown_code_blocks():
    from tallerclaro.infrastructure.ai.service import AIProposalParser

    markdown_payload = (
        "```json\n"
        '{\n'
        '  "description": "Estantería de cedro",\n'
        '  "items": [\n'
        '    {"type": "material", "description": "Cedro 2x4", "quantity": 3, "unit_price": 25.0}\n'
        '  ],\n'
        '  "assumptions": ["Barniz brillante"]\n'
        '}\n'
        "```"
    )
    result = AIProposalParser.parse(markdown_payload)
    assert not result.needs_information
    assert result.description == "Estantería de cedro"
    assert len(result.line_items) == 1
    assert result.line_items[0].unit_price == Decimal("25.0")
    assert result.assumptions == ["Barniz brillante"]


def test_openai_service_fallback_when_response_format_rejected():
    settings = Settings(ai_api_key="nvapi-test", ai_provider="openai")
    mock_client = MagicMock()

    # Primera respuesta: 400 rechazando response_format
    resp_400 = MagicMock()
    resp_400.status_code = 400
    resp_400.text = "Error: 'response_format' is not supported by this model"

    # Segunda respuesta (fallback sin response_format): 200 OK
    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.raise_for_status.return_value = None
    resp_200.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"description": "Silla", "items": [{"type": "material", "description": "Pino", "quantity": 1, "unit_price": 10}], "assumptions": []}'
                }
            }
        ]
    }
    mock_client.post.side_effect = [resp_400, resp_200]

    service = OpenAIAIService(settings=settings, client=mock_client)
    res = service.generate_quote_proposal("Fabricar una silla")
    assert res.description == "Silla"
    assert len(res.line_items) == 1
    assert mock_client.post.call_count == 2

