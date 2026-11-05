"""Pruebas aisladas de los parsers de respuestas PayPal (sin red ni base de datos)."""

from decimal import Decimal

import pytest

from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_parsing import (
    PayPalCaptureParser,
    PayPalOrderParser,
)


def _capture_payload(**overrides) -> dict:
    payload = {
        "id": "PP-EXPECTED",
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
    payload.update(overrides)
    return payload


def test_capture_parser_accepts_valid_payload_and_normalizes_utc():
    captured = PayPalCaptureParser.parse(_capture_payload(), "PP-EXPECTED")

    assert captured.paypal_order_id == "PP-EXPECTED"
    assert captured.paypal_capture_id == "CAP-1"
    assert captured.amount == Decimal("100.00")
    assert captured.currency == "USD"
    assert captured.status == "completed"
    assert captured.paid_at == "2026-11-02T21:00:00+00:00"


def test_capture_parser_falls_back_to_current_time_without_paid_at():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0].pop("update_time")

    captured = PayPalCaptureParser.parse(payload, "PP-EXPECTED")

    assert captured.paid_at


@pytest.mark.parametrize("payload", [None, [], "text", 42])
def test_capture_parser_rejects_non_object_payload(payload):
    with pytest.raises(DomainError, match="Malformed PayPal capture payload"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_capture_parser_rejects_order_not_completed():
    with pytest.raises(DomainError, match="not completed"):
        PayPalCaptureParser.parse(_capture_payload(status="PENDING"), "PP-EXPECTED")


def test_capture_parser_rejects_missing_order_id():
    with pytest.raises(DomainError, match="missing order id"):
        PayPalCaptureParser.parse(_capture_payload(id=""), "PP-EXPECTED")


def test_capture_parser_rejects_order_id_mismatch():
    with pytest.raises(DomainError, match="order id mismatch"):
        PayPalCaptureParser.parse(_capture_payload(id="PP-OTHER"), "PP-EXPECTED")


@pytest.mark.parametrize(
    "purchase_units",
    [None, [], {}, [{}], [{"payments": None}], [{"payments": {"captures": []}}]],
)
def test_capture_parser_rejects_missing_purchase_units_or_captures(purchase_units):
    with pytest.raises(DomainError, match="purchase_units|captures"):
        PayPalCaptureParser.parse(_capture_payload(purchase_units=purchase_units), "PP-EXPECTED")


def test_capture_parser_rejects_declined_capture_even_if_order_completed():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0]["status"] = "DECLINED"

    with pytest.raises(DomainError, match="not COMPLETED"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_capture_parser_rejects_missing_capture_id():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0]["id"] = "  "

    with pytest.raises(DomainError, match="missing capture id"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_capture_parser_rejects_missing_amount_or_currency():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0]["amount"] = None
    with pytest.raises(DomainError, match="missing amount"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")

    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0]["amount"] = {"value": ""}
    with pytest.raises(DomainError, match="value or currency_code"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_capture_parser_rejects_non_decimal_amount():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"] = "not-a-number"

    with pytest.raises(DomainError, match="not a valid decimal"):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_capture_parser_does_not_silently_accept_incomplete_amounts():
    payload = _capture_payload()
    payload["purchase_units"][0]["payments"]["captures"][0].pop("amount")

    with pytest.raises(DomainError):
        PayPalCaptureParser.parse(payload, "PP-EXPECTED")


def test_order_parser_extracts_approval_link():
    intent = PayPalOrderParser.parse(
        {
            "id": "PP-1",
            "links": [
                {"rel": "self", "href": "https://api.paypal.com/self"},
                {"rel": "approve", "href": "https://paypal.com/approve"},
            ],
        },
        amount="10.50",
        currency="USD",
    )

    assert intent.paypal_order_id == "PP-1"
    assert intent.amount == Decimal("10.50")
    assert intent.currency == "USD"
    assert intent.approval_url == "https://paypal.com/approve"


def test_order_parser_rejects_missing_id_or_malformed_payload():
    with pytest.raises(DomainError, match="missing order id"):
        PayPalOrderParser.parse({"links": []}, amount="10.00", currency="USD")
    with pytest.raises(DomainError, match="Malformed PayPal create order payload"):
        PayPalOrderParser.parse(None, amount="10.00", currency="USD")
