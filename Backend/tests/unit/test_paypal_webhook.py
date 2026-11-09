"""Verificación y normalización de webhooks de PayPal (Fase E)."""

from __future__ import annotations

import json

import httpx
import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_parsing import PayPalWebhookParser
from tallerclaro.infrastructure.payment.paypal_transport import (
    PayPalHttpTransport,
    PayPalResponse,
)
from tallerclaro.infrastructure.payment.paypal_webhook import (
    PayPalWebhookVerifier,
    UnconfiguredWebhookVerifier,
    build_webhook_verifier,
)

_HEADERS = {
    "paypal-transmission-id": "transmission-1",
    "paypal-transmission-time": "2026-11-09T10:00:00Z",
    "paypal-transmission-sig": "signature",
    "paypal-cert-url": "https://api.sandbox.paypal.com/cert",
    "paypal-auth-algo": "SHA256withRSA",
}


class _FakeTransport:
    def __init__(self, status_code: int = 200, verification: str = "SUCCESS") -> None:
        self.status_code = status_code
        self.verification = verification
        self.calls: list[tuple[dict, str]] = []

    def access_token(self) -> str:
        return "access-token"

    def verify_webhook_signature(self, verification: dict, access_token: str) -> PayPalResponse:
        self.calls.append((verification, access_token))
        return PayPalResponse(
            status_code=self.status_code,
            payload={"verification_status": self.verification},
        )


def _settings(webhook_id: str | None = "WEBHOOK-1") -> Settings:
    return Settings(
        paypal_mode="sandbox",
        paypal_client_id="id",
        paypal_client_secret="secret",
        paypal_return_url="https://example.org/return",
        paypal_cancel_url="https://example.org/cancel",
        paypal_webhook_id=webhook_id,
    )


def _capture_body() -> dict:
    return {
        "id": "WH-1",
        "event_type": "PAYMENT.CAPTURE.COMPLETED",
        "resource": {
            "id": "CAP-1",
            "status": "COMPLETED",
            "amount": {"value": "100.00", "currency_code": "USD"},
            "create_time": "2026-11-09T10:00:00Z",
            "supplementary_data": {"related_ids": {"order_id": "PP-1"}},
        },
    }


# --- Parser ---


def test_capture_event_parser_extracts_order_and_capture():
    event = PayPalWebhookParser.parse(_capture_body())

    assert event.id == "WH-1"
    assert event.type == "PAYMENT.CAPTURE.COMPLETED"
    assert event.paypal_order_id == "PP-1"
    assert event.capture is not None
    assert event.capture.paypal_capture_id == "CAP-1"
    assert str(event.capture.amount) == "100.00"


def test_order_event_parser_uses_resource_id():
    event = PayPalWebhookParser.parse(
        {
            "id": "WH-2",
            "event_type": "checkout.order.approved",
            "resource": {"id": "PP-9"},
        }
    )

    assert event.type == "CHECKOUT.ORDER.APPROVED"
    assert event.paypal_order_id == "PP-9"
    assert event.capture is None


@pytest.mark.parametrize(
    "body, message",
    [
        ({"event_type": "PAYMENT.CAPTURE.COMPLETED"}, "missing id or event_type"),
        ({"id": "WH-3"}, "missing id or event_type"),
        ("not-a-dict", "Malformed"),
    ],
)
def test_parser_rejects_incomplete_events(body, message):
    with pytest.raises(DomainError, match=message):
        PayPalWebhookParser.parse(body)


def test_capture_event_without_related_order_has_no_order_id():
    body = _capture_body()
    body["resource"].pop("supplementary_data")

    event = PayPalWebhookParser.parse(body)

    assert event.paypal_order_id is None
    assert event.capture is not None


# --- Verificador ---


def test_verifier_calls_paypal_and_returns_the_event():
    transport = _FakeTransport()
    verifier = PayPalWebhookVerifier(_settings(), transport=transport)
    body = json.dumps(_capture_body()).encode()

    event = verifier.verify(_HEADERS, body)

    assert event.id == "WH-1"
    verification, token = transport.calls[0]
    assert token == "access-token"
    assert verification["webhook_id"] == "WEBHOOK-1"
    assert verification["transmission_id"] == "transmission-1"
    assert verification["webhook_event"]["id"] == "WH-1"


def test_verifier_rejects_a_signature_paypal_does_not_confirm():
    verifier = PayPalWebhookVerifier(
        _settings(), transport=_FakeTransport(verification="FAILURE")
    )

    with pytest.raises(DomainError) as raised:
        verifier.verify(_HEADERS, json.dumps(_capture_body()).encode())

    assert raised.value.code == "UNAUTHORIZED"


def test_verifier_rejects_a_provider_error_during_verification():
    verifier = PayPalWebhookVerifier(
        _settings(), transport=_FakeTransport(status_code=500)
    )

    with pytest.raises(DomainError) as raised:
        verifier.verify(_HEADERS, json.dumps(_capture_body()).encode())

    assert raised.value.code == "PAYMENT_PROVIDER_ERROR"


def test_verifier_requires_configuration_and_headers():
    unconfigured = PayPalWebhookVerifier(_settings(webhook_id=None), transport=_FakeTransport())
    with pytest.raises(DomainError) as raised:
        unconfigured.verify(_HEADERS, b"{}")
    assert raised.value.code == "SERVICE_UNAVAILABLE"

    verifier = PayPalWebhookVerifier(_settings(), transport=_FakeTransport())
    with pytest.raises(DomainError) as raised:
        verifier.verify({"paypal-transmission-id": "only-one"}, b"{}")
    assert raised.value.code == "UNAUTHORIZED"


def test_verifier_rejects_a_body_that_is_not_json():
    verifier = PayPalWebhookVerifier(_settings(), transport=_FakeTransport())

    with pytest.raises(DomainError) as raised:
        verifier.verify(_HEADERS, b"not-json")

    assert raised.value.code == "VALIDATION_ERROR"


# --- Transporte y construcción ---


def test_transport_posts_the_verification_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"verification_status": "SUCCESS"})

    settings = _settings()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        transport = PayPalHttpTransport(settings, client=client)
        response = transport.verify_webhook_signature({"webhook_id": "WEBHOOK-1"}, "token")

    assert response.status_code == 200
    assert captured["url"].endswith("/v1/notifications/verify-webhook-signature")
    assert captured["body"] == {"webhook_id": "WEBHOOK-1"}
    assert captured["auth"] == "Bearer token"


def test_builder_returns_unconfigured_without_paypal_credentials():
    assert isinstance(build_webhook_verifier(Settings(paypal_mode="none")), UnconfiguredWebhookVerifier)
    assert isinstance(build_webhook_verifier(_settings()), PayPalWebhookVerifier)


def test_unconfigured_verifier_rejects_every_event():
    with pytest.raises(DomainError) as raised:
        UnconfiguredWebhookVerifier().verify({}, b"{}")
    assert raised.value.code == "SERVICE_UNAVAILABLE"
