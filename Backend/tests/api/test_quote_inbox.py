"""Bandeja del taller (GET /api/quotes), avance de pedido tras el anticipo y código corto."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tallerclaro.domain.entities import (
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    PAYMENT_STATUS_COMPLETED,
    PAYMENT_TYPE_BALANCE,
    PAYMENT_TYPE_DEPOSIT,
    Carpenter,
    CarpenterId,
    Money,
    Order,
    OrderId,
    Payment,
)
from tallerclaro.infrastructure.db.repositories import PostgresQuoteRepository
from tests.api.test_auth import unmocked_auth_app  # noqa: F401  (fixture)
from tests.fakes import FakeDependenciesContainer
from tests.unit.test_repository_contracts import ScriptedConnection

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _seed(deps: FakeDependenciesContainer) -> None:
    with deps.uow:
        deps.uow.carpenters.seed(
            Carpenter(id=CarpenterId(1), name="José", workshop_name="Madera Norte", email="j@example.com", phone=None)
        )
        deps.uow.carpenters.seed(
            Carpenter(id=CarpenterId(2), name="Otro", workshop_name="Otro", email="o@example.com", phone=None)
        )
        deps.uow.commit()


def _create(client: TestClient, carpenter_id: int = 1, name: str = "Lucía") -> str:
    resp = client.post(
        "/api/quotes",
        json={
            "customer": {"name": name, "email": f"{name.lower()}@example.com"},
            "carpenter_id": carpenter_id,
            "request": "Ropero de dos puertas",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_quotes_returns_only_own_workshop_with_customer(client: TestClient, deps):
    _seed(deps)
    first = _create(client, name="Lucia")
    _create(client, carpenter_id=2, name="Ajeno")
    second = _create(client, name="Mario")

    resp = client.get("/api/quotes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [q["id"] for q in data["quotes"]] == [second, first]
    assert data["quotes"][0]["customer_name"] == "Mario"
    assert data["quotes"][0]["customer_token"] is None


def test_list_quotes_filters_by_status(client: TestClient, deps):
    _seed(deps)
    draft = _create(client)
    generated = _create(client, name="Mario")
    assert client.post(f"/api/quotes/{generated}/generate").status_code == 200

    only_draft = client.get("/api/quotes", params={"status": "draft"}).json()
    assert [q["id"] for q in only_draft["quotes"]] == [draft]

    both = client.get("/api/quotes", params={"status": "draft,pending_review"}).json()
    assert both["total"] == 2

    repeated = client.get("/api/quotes?status=draft&status=pending_review").json()
    assert repeated["total"] == 2


def test_list_quotes_rejects_unknown_status(client: TestClient, deps):
    _seed(deps)
    resp = client.get("/api/quotes", params={"status": "bogus"})
    assert resp.status_code == 422


def test_list_quotes_paginates(client: TestClient, deps):
    _seed(deps)
    for name in ("A", "B", "C"):
        _create(client, name=name)
    page = client.get("/api/quotes", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 3 and len(page["quotes"]) == 1


def test_list_quotes_requires_workshop_auth(unmocked_auth_app):
    client, *_ = unmocked_auth_app
    assert client.get("/api/quotes").status_code == 401
    assert client.get("/api/quotes", auth=("taller", "wrong")).status_code == 401

    created = client.post(
        "/api/quotes",
        json={"customer": {"name": "Ana", "email": "ana@example.com"}, "carpenter_id": 1, "request": "Mesa"},
    ).json()
    customer_headers = {"X-Customer-Token": created["customer_token"]}
    assert client.get("/api/quotes", headers=customer_headers).status_code == 401

    resp = client.get("/api/quotes", auth=("taller", "demo-password"))
    assert resp.status_code == 200
    assert resp.json()["quotes"][0]["customer_name"] == "Ana"


def test_postgres_quote_listing_sql_filters_by_workshop_and_status():
    quote_row = (5, 1, 2, "Mesa", None, None, "draft", "USD", NOW, NOW, [], [])
    conn = ScriptedConnection([quote_row], [], (1,))
    repo = PostgresQuoteRepository(conn)

    quotes = repo.list_by_carpenter(2, ("draft",), 10, 0)
    assert [q.id for q in quotes] == [5]
    assert repo.count_by_carpenter(2, ("draft",)) == 1

    list_sql, list_params = conn.calls[0]
    assert "WHERE id_carpintero = %s" in list_sql
    assert "estado = ANY" in list_sql and "LIMIT %s OFFSET %s" in list_sql
    assert list_params == (2, ["draft"], ["draft"], 10, 0)
    assert conn.calls[2][1] == (2, ["draft"], ["draft"])
    assert all("DELETE" not in sql for sql, _ in conn.calls)
    assert conn.responses == []


def _order(status: str = ORDER_STATUS_PENDING) -> Order:
    return Order(OrderId(1), 1, CarpenterId(1), "TC-1001", Money("200"), Money("100"), "USD", status, NOW, NOW)


def _paid(kind: str, amount: str) -> Payment:
    return Payment(None, OrderId(1), kind, Money(amount), "USD", PAYMENT_STATUS_COMPLETED, "PP", "CAP", NOW, NOW, NOW)


def test_deposit_moves_pending_order_to_in_progress():
    order = _order()
    order.advance_after_payment([_paid(PAYMENT_TYPE_DEPOSIT, "100")])
    assert order.status == ORDER_STATUS_IN_PROGRESS


def test_full_payment_on_pending_order_marks_paid():
    order = _order()
    order.advance_after_payment([_paid(PAYMENT_TYPE_DEPOSIT, "100"), _paid(PAYMENT_TYPE_BALANCE, "100")])
    assert order.status == ORDER_STATUS_PAID


@pytest.mark.parametrize("status", [ORDER_STATUS_IN_PROGRESS, "delivered", "cancelled"])
def test_non_pending_order_status_is_untouched(status):
    order = _order(status)
    order.advance_after_payment([_paid(PAYMENT_TYPE_DEPOSIT, "100"), _paid(PAYMENT_TYPE_BALANCE, "100")])
    assert order.status == status


def test_order_code_is_short_and_derived_from_quote():
    assert Order.code_for_quote(48) == "TC-1048"


def test_approved_order_gets_short_code_and_deposit_capture_starts_work(client: TestClient, deps):
    _seed(deps)
    quote_id = _create(client)
    assert client.post(f"/api/quotes/{quote_id}/generate").status_code == 200
    order = client.post(f"/api/quotes/{quote_id}/approve").json()
    assert order["code"] == f"TC-{1000 + int(quote_id)}"
    assert order["status"] == ORDER_STATUS_PENDING

    payment = client.post(f"/api/orders/{order['id']}/payments", json={"type": "deposit"}).json()
    assert client.post(f"/api/payments/{payment['payment_id']}/capture").status_code == 200

    detail = client.get(f"/api/orders/{order['id']}").json()
    assert detail["status"] == ORDER_STATUS_IN_PROGRESS
