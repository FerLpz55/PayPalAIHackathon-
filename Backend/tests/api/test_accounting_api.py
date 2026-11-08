"""Pruebas HTTP del asistente contable."""

from datetime import datetime, timezone
import bcrypt
from fastapi.testclient import TestClient

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId, Money, Order, Payment, QuoteId
from tallerclaro.infrastructure.ai.accounting_service import UnconfiguredAccountingAssistant
from tests.fakes import FakeDependenciesContainer


def _seed(deps: FakeDependenciesContainer) -> None:
    with deps.uow:
        order = deps.uow.orders.save(
            Order(
                id=None,
                quote_id=QuoteId(1),
                carpenter_id=CarpenterId(1),
                code="TC-1048",
                total=Money("1200"),
                deposit_amount=Money("600"),
                currency="USD",
                status="in_progress",
                created_at=None,
                updated_at=None,
            )
        )
        deps.uow.payments.save(
            Payment(
                id=None,
                order_id=order.id,
                type="deposit",
                amount=Money("600"),
                currency="USD",
                status="completed",
                paypal_order_id="P-1",
                paypal_capture_id="C-1",
                created_at=None,
                updated_at=None,
                paid_at=datetime.now(timezone.utc),
            )
        )
        deps.uow.commit()


def test_summary_endpoint_returns_workshop_totals(client: TestClient, deps: FakeDependenciesContainer):
    _seed(deps)
    response = client.get("/api/accounting/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "USD"
    assert data["orders_count"] == 1
    assert data["total_contracted"] == 1200.0
    assert data["collected_total"] == 600.0
    assert data["pending_to_collect"] == 600.0


def test_assistant_endpoint_returns_answer_and_summary(client: TestClient, deps: FakeDependenciesContainer):
    _seed(deps)
    response = client.post("/api/accounting/assistant", json={"question": "How much did I collect?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Your workshop is doing fine."
    assert data["summary"]["collected_total"] == 600.0
    assert deps.accounting.calls[0][1] == "How much did I collect?"


def test_assistant_endpoint_validates_question(client: TestClient):
    response = client.post("/api/accounting/assistant", json={"question": "hi"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_assistant_endpoint_without_ai_returns_503(deps: FakeDependenciesContainer):
    from tallerclaro.main import create_app
    from tallerclaro.presentation.http.dependencies import get_unit_of_work, require_workshop_credentials
    from tallerclaro.application.dtos import AccessPrincipal

    password_hash = bcrypt.hashpw(b"demo-password", bcrypt.gensalt(rounds=4)).decode()
    app = create_app(
        settings=Settings(workshop_username="taller", workshop_password_hash=password_hash),
        ai_service=deps.ai,
        payment_processor=deps.payment,
        accounting_assistant=UnconfiguredAccountingAssistant(),
    )
    app.dependency_overrides[get_unit_of_work] = lambda: deps.uow
    app.dependency_overrides[require_workshop_credentials] = lambda: AccessPrincipal(
        kind="workshop", carpenter_id=CarpenterId(1)
    )
    response = TestClient(app).post("/api/accounting/assistant", json={"question": "How am I doing?"})
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"


def test_accounting_endpoints_require_workshop_credentials(deps: FakeDependenciesContainer):
    from tallerclaro.main import create_app
    from tallerclaro.presentation.http.dependencies import get_unit_of_work

    password_hash = bcrypt.hashpw(b"demo-password", bcrypt.gensalt(rounds=4)).decode()
    app = create_app(
        settings=Settings(workshop_username="taller", workshop_password_hash=password_hash),
        ai_service=deps.ai,
        payment_processor=deps.payment,
        accounting_assistant=deps.accounting,
    )
    app.dependency_overrides[get_unit_of_work] = lambda: deps.uow
    test_client = TestClient(app)

    assert test_client.get("/api/accounting/summary").status_code == 401
    assert test_client.post("/api/accounting/assistant", json={"question": "How am I doing?"}).status_code == 401
    assert test_client.get("/api/accounting/summary", auth=("taller", "wrong")).status_code == 401
    assert test_client.get("/api/accounting/summary", auth=("taller", "demo-password")).status_code == 200
    assert deps.accounting.calls == []

