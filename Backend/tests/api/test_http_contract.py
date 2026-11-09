"""Inventario del contrato HTTP para detectar cambios de rutas o métodos."""

from __future__ import annotations

from tallerclaro.bootstrap.settings import Settings
from tests.fakes import FakeAIService, FakePaymentProcessor

EXPECTED_OPERATIONS = {
    ("get", "/api/health"),
    ("post", "/api/auth/login"),
    ("get", "/api/auth/session"),
    ("post", "/api/auth/logout"),
    ("get", "/api/customer/context"),
    ("get", "/api/accounting/summary"),
    ("post", "/api/accounting/assistant"),
    ("post", "/api/quotes"),
    ("get", "/api/quotes/{quote_id}"),
    ("post", "/api/quotes/{quote_id}/generate"),
    ("post", "/api/quotes/{quote_id}/approve"),
    ("post", "/api/quotes/{quote_id}/reject"),
    ("post", "/api/quotes/{quote_id}/customer-access"),
    ("get", "/api/orders"),
    ("get", "/api/orders/{order_id}"),
    ("patch", "/api/orders/{order_id}"),
    ("post", "/api/orders/{order_id}/payments"),
    ("get", "/api/payments/{payment_id}"),
    ("post", "/api/payments/{payment_id}/capture"),
    ("post", "/api/payments/{payment_id}/sync"),
    ("post", "/api/payments/{payment_id}/cancel"),
}


def test_openapi_route_inventory_is_unchanged():
    from tallerclaro.main import create_app

    app = create_app(
        settings=Settings(),
        ai_service=FakeAIService(),
        payment_processor=FakePaymentProcessor(),
    )

    operations = {
        (method, path)
        for path, methods in app.openapi()["paths"].items()
        for method in methods
    }

    assert operations == EXPECTED_OPERATIONS


def test_payment_endpoints_keep_their_response_fields():
    from tallerclaro.main import create_app

    app = create_app(
        settings=Settings(),
        ai_service=FakeAIService(),
        payment_processor=FakePaymentProcessor(),
    )
    schema = app.openapi()["components"]["schemas"]

    assert set(schema["PaymentIntentResponse"]["properties"]) == {
        "payment_id",
        "paypal_order_id",
        "amount",
        "currency",
        "approval_url",
    }
    assert set(schema["CapturePaymentResponse"]["properties"]) == {
        "payment_id",
        "status",
        "paypal_order_id",
        "paypal_capture_id",
        "amount",
        "currency",
        "paid_at",
    }
    assert set(schema["PaymentResponse"]["properties"]) >= {
        "id",
        "order_id",
        "type",
        "amount",
        "currency",
        "status",
        "paypal_order_id",
        "paypal_capture_id",
        "created_at",
        "paid_at",
    }
