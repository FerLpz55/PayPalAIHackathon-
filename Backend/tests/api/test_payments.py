"""Pruebas HTTP de pagos."""

from fastapi.testclient import TestClient

from tallerclaro.domain.entities import Carpenter, CarpenterId
from tests.fakes import FakeDependenciesContainer


def _create_approved_order(client: TestClient, deps: FakeDependenciesContainer):
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
    order_response = client.post(
        f"/api/quotes/{quote_id}/approve",
        headers={"X-Customer-Token": token},
    )
    return order_response.json()["id"], token


def test_create_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id, token = _create_approved_order(client, deps)
    response = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100.0
    assert data["currency"] == "USD"


def test_capture_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id, token = _create_approved_order(client, deps)
    payment_response = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    )
    payment_id = payment_response.json()["payment_id"]

    response = client.post(
        f"/api/payments/{payment_id}/capture",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"


def test_get_payment(client: TestClient, deps: FakeDependenciesContainer):
    order_id, token = _create_approved_order(client, deps)
    payment_response = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    )
    payment_id = payment_response.json()["payment_id"]

    response = client.get(
        f"/api/payments/{payment_id}",
        headers={"X-Customer-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["id"] == payment_id


def test_capture_transport_timeout_returns_502_and_keeps_reservation(client, deps):
    import httpx
    from tallerclaro.bootstrap.settings import Settings
    from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor

    order_id, token = _create_approved_order(client, deps)
    payment = client.post(f'/api/orders/{order_id}/payments', json={'type': 'deposit'}).json()
    def timeout(request):
        raise httpx.ReadTimeout('secret', request=request)
    settings = Settings(paypal_mode='sandbox', paypal_client_id='id', paypal_client_secret='secret', paypal_return_url='https://example.org/return', paypal_cancel_url='https://example.org/cancel')
    with httpx.Client(transport=httpx.MockTransport(timeout)) as http:
        client.app.state.payment_processor = PayPalPaymentProcessor(settings, client=http)
        response = client.post(f"/api/payments/{payment['payment_id']}/capture", headers={'X-Customer-Token': token})
    assert response.status_code == 502
    assert response.json()['code'] == 'PAYMENT_PROVIDER_ERROR'
    assert set(response.json()) == {'code', 'message'}
    assert 'secret' not in response.text
    with deps.uow:
        assert deps.uow.payments.get_by_id(int(payment['payment_id'])).status == 'pending'
    with deps.uow:
        assert deps.uow.capture_reservations._captures[int(order_id)] == int(payment['payment_id'])
