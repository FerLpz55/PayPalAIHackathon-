from unittest.mock import MagicMock

import pytest

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_processor import PayPalPaymentProcessor


def test_paypal_requires_configured_return_urls():
    settings = Settings(paypal_mode="sandbox")
    with pytest.raises(DomainError, match="return"):
        PayPalPaymentProcessor(settings)


def test_paypal_sends_configured_return_urls():
    settings = Settings(paypal_mode="sandbox", paypal_client_id="id", paypal_client_secret="secret", paypal_return_url="https://example.org/#/return", paypal_cancel_url="https://example.org/#/cancel")
    client = MagicMock()
    client.post.side_effect = [MagicMock(status_code=200, json=lambda: {"access_token": "token"}), MagicMock(status_code=201, json=lambda: {"id": "order", "links": []})]
    PayPalPaymentProcessor(settings, client).create_order("10.00", "USD")
    context = client.post.call_args.kwargs["json"]["application_context"]
    assert context == {
        "return_url": settings.paypal_return_url,
        "cancel_url": settings.paypal_cancel_url,
        "user_action": "PAY_NOW",
        "shipping_preference": "NO_SHIPPING",
        "brand_name": settings.paypal_brand_name,
    }


def test_paypal_recovers_already_captured_order():
    settings = Settings(paypal_mode="sandbox", paypal_client_id="id", paypal_client_secret="secret", paypal_return_url="https://example.org/return", paypal_cancel_url="https://example.org/cancel")
    client = MagicMock()
    client.post.side_effect = [MagicMock(status_code=200, json=lambda: {"access_token": "token"}), MagicMock(status_code=422)]
    client.get.return_value = MagicMock(status_code=200, json=lambda: {"id": "order", "status": "COMPLETED", "purchase_units": [{"payments": {"captures": [{"id": "capture", "status": "COMPLETED", "amount": {"value": "10.00", "currency_code": "USD"}}]}}]})
    result = PayPalPaymentProcessor(settings, client).capture_order("order")
    assert result.paypal_capture_id == "capture"
    assert client.post.call_args.kwargs["headers"]["PayPal-Request-Id"]
