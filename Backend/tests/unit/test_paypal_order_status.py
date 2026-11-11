"""Estado de orden PayPal y parámetros de checkout (Fase D)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_parsing import PayPalOrderStatusParser
from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor


def _settings() -> Settings:
    return Settings(
        paypal_mode="sandbox",
        paypal_client_id="id",
        paypal_client_secret="secret",
        paypal_return_url="https://example.org/return",
        paypal_cancel_url="https://example.org/cancel",
    )


def _approved_payload(status: str = "APPROVED") -> dict:
    return {
        "id": "PP-1",
        "status": status,
        "links": [
            {"rel": "approve", "href": "https://sandbox.paypal.com/checkoutnow?token=PP-1"}
        ],
    }


def test_status_parser_reports_approval_link_without_capture():
    order = PayPalOrderStatusParser.parse(_approved_payload(), "PP-1")

    assert order.status == "APPROVED"
    assert order.capture is None
    assert order.approval_url.endswith("token=PP-1")


def test_status_parser_extracts_existing_capture_when_completed():
    payload = {
        "id": "PP-1",
        "status": "COMPLETED",
        "purchase_units": [
            {
                "payments": {
                    "captures": [
                        {
                            "id": "CAP-1",
                            "status": "COMPLETED",
                            "amount": {"value": "100.00", "currency_code": "USD"},
                            "update_time": "2026-11-02T21:00:00Z",
                        }
                    ]
                }
            }
        ],
    }

    order = PayPalOrderStatusParser.parse(payload, "PP-1")

    assert order.status == "COMPLETED"
    assert order.capture is not None
    assert order.capture.paypal_capture_id == "CAP-1"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"id": "OTHER"}, "id mismatch"),
        ({"status": ""}, "missing status"),
        ({"id": ""}, "missing order id"),
    ],
)
def test_status_parser_rejects_invalid_identity(overrides, message):
    payload = _approved_payload()
    payload.update(overrides)

    with pytest.raises(DomainError, match=message):
        PayPalOrderStatusParser.parse(payload, "PP-1")


def test_create_order_sends_paypal_request_id_and_checkout_preferences():
    settings = _settings()
    client = MagicMock()
    client.post.side_effect = [
        MagicMock(status_code=200, json=lambda: {"access_token": "token"}),
        MagicMock(status_code=201, json=lambda: {"id": "order", "links": []}),
    ]

    PayPalPaymentProcessor(settings, client).create_order(
        "10.00", "USD", request_id="idempotency-key-1"
    )

    create_call = client.post.call_args
    assert create_call.kwargs["headers"]["PayPal-Request-Id"] == "idempotency-key-1"
    context = create_call.kwargs["json"]["application_context"]
    assert context["user_action"] == "PAY_NOW"
    assert context["shipping_preference"] == "NO_SHIPPING"
    assert context["brand_name"] == "TallerClaro"


def test_get_order_reads_provider_status_without_capturing():
    settings = _settings()
    client = MagicMock()
    client.post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "token"}
    )
    client.get.return_value = MagicMock(
        status_code=200, json=lambda: _approved_payload("APPROVED")
    )
    processor = PayPalPaymentProcessor(settings, client)

    order = processor.get_order("PP-1")

    assert order.status == "APPROVED"
    client.get.assert_called_once()
    client.post.assert_called_once()  # solo OAuth, ninguna captura


def test_get_order_rejects_non_success_status():
    settings = _settings()
    client = MagicMock()
    client.post.return_value = MagicMock(
        status_code=200, json=lambda: {"access_token": "token"}
    )
    client.get.return_value = MagicMock(status_code=500)

    with pytest.raises(DomainError) as raised:
        PayPalPaymentProcessor(settings, client).get_order("PP-1")
    assert raised.value.code == "PAYMENT_PROVIDER_ERROR"
