"""Pruebas HTTP de pedidos."""

from fastapi.testclient import TestClient

from tallerclaro.domain.entities import Carpenter, CarpenterId
from tests.fakes import FakeDependenciesContainer


def _seed_and_create_quote(client: TestClient, deps: FakeDependenciesContainer):
    deps.uow.carpenters.seed(
        Carpenter(
            id=CarpenterId(1),
            name="José",
            workshop_name="Taller",
            email="j@example.com",
            phone=None,
        )
    )
    response = client.post("/api/quotes", json={
        "customer": {"name": "Carlos", "email": "carlos@example.com"},
        "carpenter_id": 1,
        "request": "Mesa",
    })
    quote_id = response.json()["id"]
    client.post(f"/api/quotes/{quote_id}/generate")
    return quote_id


def test_approve_quote_returns_order(client: TestClient, deps: FakeDependenciesContainer):
    quote_id = _seed_and_create_quote(client, deps)
    response = client.post(f"/api/quotes/{quote_id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["quote_id"] == quote_id
    assert data["status"] == "pending"


def test_list_orders(client: TestClient, deps: FakeDependenciesContainer):
    quote_id = _seed_and_create_quote(client, deps)
    client.post(f"/api/quotes/{quote_id}/approve")

    response = client.get("/api/orders?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["orders"]) == 1


def test_update_order_status(client: TestClient, deps: FakeDependenciesContainer):
    quote_id = _seed_and_create_quote(client, deps)
    order_response = client.post(f"/api/quotes/{quote_id}/approve")
    order_id = order_response.json()["id"]

    response = client.patch(f"/api/orders/{order_id}", json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
