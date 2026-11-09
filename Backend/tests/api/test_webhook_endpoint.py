"""Contrato HTTP del webhook de PayPal (Fase E)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tallerclaro.application.dtos import WebhookEvent
from tallerclaro.domain.entities import Carpenter, CarpenterId
from tallerclaro.domain.exceptions import DomainError
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
    response = client.post(
        "/api/quotes",
        json={
            "customer": {"name": "Carlos", "email": "carlos@example.com"},
            "carpenter_id": 1,
            "request": "Mesa",
        },
    )
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


def test_webhook_needs_no_customer_token_and_reconciles(client, deps):
    order_id, token = _create_approved_order(client, deps)
    intent = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    ).json()
    deps.payment.set_order_status(intent["paypal_order_id"], "APPROVED")
    deps.webhook.queue(
        WebhookEvent(
            id="WH-API-1",
            type="PAYMENT.CAPTURE.COMPLETED",
            paypal_order_id=intent["paypal_order_id"],
        )
    )

    response = client.post(
        "/api/payments/webhook/paypal",
        content=b'{"id": "WH-API-1"}',
        headers={
            "Content-Type": "application/json",
            "Paypal-Transmission-Id": "transmission-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    with deps.uow:
        payment = deps.uow.payments.get_by_id(int(intent["payment_id"]))
        assert payment.status == "completed"


def test_webhook_duplicate_returns_duplicate_status(client, deps):
    order_id, token = _create_approved_order(client, deps)
    intent = client.post(
        f"/api/orders/{order_id}/payments",
        json={"type": "deposit"},
        headers={"X-Customer-Token": token},
    ).json()
    deps.payment.set_order_status(intent["paypal_order_id"], "APPROVED")
    event = WebhookEvent(
        id="WH-API-2",
        type="PAYMENT.CAPTURE.COMPLETED",
        paypal_order_id=intent["paypal_order_id"],
    )

    deps.webhook.queue(event)
    first = client.post(
        "/api/payments/webhook/paypal", content=b"{}",
        headers={"Content-Type": "application/json"},
    )
    deps.webhook.queue(event)
    second = client.post(
        "/api/payments/webhook/paypal", content=b"{}",
        headers={"Content-Type": "application/json"},
    )

    assert first.json() == {"status": "processed"}
    assert second.json() == {"status": "duplicate"}


def test_webhook_rejects_an_invalid_signature(client, deps):
    deps.webhook.error = DomainError(
        code="UNAUTHORIZED", message="PayPal webhook signature was not verified"
    )

    response = client.post(
        "/api/payments/webhook/paypal",
        content=b"{}",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_webhook_reports_unconfigured_verification_as_unavailable(client, deps):
    deps.webhook.error = DomainError(
        code="SERVICE_UNAVAILABLE", message="PayPal webhook verification is not configured"
    )

    response = client.post(
        "/api/payments/webhook/paypal",
        content=b"{}",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
