"""Pruebas HTTP de pagos."""

from fastapi.testclient import TestClient

from tallerclaro.domain.entities import Carpenter, CarpenterId
from tests.fakes import FakeDependenciesContainer


def _create_approved_order(client: TestClient, deps: FakeDependenciesContainer):
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
    order_response = client.post(f"/api/quotes/{quote_id}/approve")
    return order_response.json()["id"]


def test_create_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id = _create_approved_order(client, deps)
    response = client.post(f"/api/orders/{order_id}/payments", json={"type": "deposit"})
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100.0
    assert data["currency"] == "USD"


def test_capture_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id = _create_approved_order(client, deps)
    payment_response = client.post(f"/api/orders/{order_id}/payments", json={"type": "deposit"})
    payment_id = payment_response.json()["payment_id"]

    response = client.post(f"/api/payments/{payment_id}/capture")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"


def test_get_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id = _create_approved_order(client, deps)
    payment_response = client.post(f"/api/orders/{order_id}/payments", json={"type": "deposit"})
    payment_id = payment_response.json()["payment_id"]

    response = client.get(f"/api/payments/{payment_id}")
    assert response.status_code == 200
    assert response.json()["id"] == payment_id
