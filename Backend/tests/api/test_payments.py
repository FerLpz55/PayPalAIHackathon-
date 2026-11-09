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


def test_create_payment_is_idempotent_for_the_same_pending_attempt(client, deps):
    order_id, token = _create_approved_order(client, deps)
    headers = {"X-Customer-Token": token}
    first = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    )
    second = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["payment_id"] == first.json()["payment_id"]
    assert second.json()["paypal_order_id"] == first.json()["paypal_order_id"]
    assert second.json()["approval_url"] == first.json()["approval_url"]


def test_sync_endpoint_leaves_payment_pending_without_capturing(client, deps):
    order_id, token = _create_approved_order(client, deps)
    headers = {"X-Customer-Token": token}
    intent = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    ).json()

    response = client.post(f"/api/payments/{intent['payment_id']}/sync", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert deps.payment.capture_calls == []


def test_cancel_endpoint_marks_payment_cancelled(client, deps):
    order_id, token = _create_approved_order(client, deps)
    headers = {"X-Customer-Token": token}
    intent = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    ).json()

    response = client.post(f"/api/payments/{intent['payment_id']}/cancel", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_endpoint_rejects_a_completed_payment(client, deps):
    order_id, token = _create_approved_order(client, deps)
    headers = {"X-Customer-Token": token}
    intent = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    ).json()
    client.post(f"/api/payments/{intent['payment_id']}/capture", headers=headers)

    response = client.post(f"/api/payments/{intent['payment_id']}/cancel", headers=headers)

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_order_detail_exposes_derived_financial_status(client, deps):
    order_id, token = _create_approved_order(client, deps)
    headers = {"X-Customer-Token": token}

    pending = client.get(f"/api/orders/{order_id}", headers=headers)
    assert pending.status_code == 200
    assert pending.json()["financial_status"] == "unpaid"

    intent = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "deposit"}, headers=headers
    ).json()
    client.post(f"/api/payments/{intent['payment_id']}/capture", headers=headers)

    paid_deposit = client.get(f"/api/orders/{order_id}", headers=headers)
    assert paid_deposit.json()["financial_status"] == "deposit_paid"

    balance = client.post(
        f"/api/orders/{order_id}/payments", json={"type": "balance"}, headers=headers
    ).json()
    client.post(f"/api/payments/{balance['payment_id']}/capture", headers=headers)

    fully_paid = client.get(f"/api/orders/{order_id}", headers=headers)
    assert fully_paid.json()["financial_status"] == "paid"
