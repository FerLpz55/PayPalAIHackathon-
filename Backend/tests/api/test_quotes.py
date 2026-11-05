"""Pruebas HTTP de cotizaciones."""

from fastapi.testclient import TestClient

from tests.fakes import FakeDependenciesContainer


def _seed_carpenter(deps: FakeDependenciesContainer):
    from tallerclaro.domain.entities import Carpenter, CarpenterId
    deps.uow.carpenters.seed(
        Carpenter(
            id=CarpenterId(1),
            name="José",
            workshop_name="Taller",
            email="j@example.com",
            phone=None,
        )
    )


def test_create_quote(client: TestClient, deps: FakeDependenciesContainer):
    _seed_carpenter(deps)
    response = client.post("/api/quotes", json={
        "customer": {"name": "Carlos", "email": "carlos@example.com"},
        "carpenter_id": 1,
        "request": "Mesa de centro",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["customer_id"] == "1"
    assert data["customer_token"] is not None
    assert len(data["customer_token"]) > 0


def test_generate_quote(client: TestClient, deps: FakeDependenciesContainer):
    _seed_carpenter(deps)
    response = client.post("/api/quotes", json={
        "customer": {"name": "Carlos", "email": "carlos@example.com"},
        "carpenter_id": 1,
        "request": "Mesa de centro",
    })
    quote_id = response.json()["id"]

    response = client.post(
        f"/api/quotes/{quote_id}/generate",
        auth=("taller", "demo-password"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending_review"
    assert data["total"] == 200.0


def test_get_quote(client: TestClient, deps: FakeDependenciesContainer):
    _seed_carpenter(deps)
    response = client.post("/api/quotes", json={
        "customer": {"name": "Carlos", "email": "carlos@example.com"},
        "carpenter_id": 1,
        "request": "Mesa",
    })
    quote_id = response.json()["id"]
    token = response.json()["customer_token"]

    response = client.get(
        f"/api/quotes/{quote_id}",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["id"] == quote_id


def test_get_quote_not_found(client: TestClient, deps: FakeDependenciesContainer):
    response = client.get(
        "/api/quotes/9999",
        auth=("taller", "demo-password"),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
