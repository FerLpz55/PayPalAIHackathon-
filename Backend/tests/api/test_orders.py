"""Pruebas HTTP de pedidos."""

from fastapi.testclient import TestClient

from tallerclaro.domain.entities import Carpenter, CarpenterId
from tests.fakes import FakeDependenciesContainer


def _seed_and_create_quote(client: TestClient, deps: FakeDependenciesContainer):
    with deps.uow:
        deps.uow.carpenters.seed(
            Carpenter(
                id=CarpenterId(1),
                name="José",
                workshop_name="Taller",
                email="j@example.com",
                phone=None,
            )
        )
        deps.uow.commit()
    response = client.post("/api/quotes", json={
        "customer": {"name": "Carlos", "email": "carlos@example.com"},
        "carpenter_id": 1,
        "request": "Mesa",
    })
    data = response.json()
    quote_id = data["id"]
    token = data["customer_token"]
    client.post(
        f"/api/quotes/{quote_id}/generate",
        auth=("taller", "demo-password"),
    )
    return quote_id, token


def test_approve_quote_returns_order(client: TestClient, deps: FakeDependenciesContainer):
    quote_id, token = _seed_and_create_quote(client, deps)
    response = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["quote_id"] == quote_id
    assert data["status"] == "pending"


def test_get_order(client: TestClient, deps: FakeDependenciesContainer):
    quote_id, token = _seed_and_create_quote(client, deps)
    order_response = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )
    order_id = order_response.json()["id"]

    response = client.get(
        f"/api/orders/{order_id}",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["quote_id"] == quote_id
    assert data["customer_name"] == "Carlos"
    assert data["customer_email"] == "carlos@example.com"
    assert data["project_request"] == "Mesa"
    assert isinstance(data["payments"], list)


def test_list_orders(client: TestClient, deps: FakeDependenciesContainer):
    quote_id, token = _seed_and_create_quote(client, deps)
    client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )

    response = client.get(
        "/api/orders?limit=10&offset=0",
        auth=("taller", "demo-password"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["orders"]) == 1


def test_update_order_status(client: TestClient, deps: FakeDependenciesContainer):
    quote_id, token = _seed_and_create_quote(client, deps)
    order_response = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )
    order_id = order_response.json()["id"]

    response = client.patch(
        f"/api/orders/{order_id}",
        json={"status": "in_progress"},
        auth=("taller", "demo-password"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
