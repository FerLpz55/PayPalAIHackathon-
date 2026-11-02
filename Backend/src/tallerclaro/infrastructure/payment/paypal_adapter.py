"""Adaptador de PayPal Sandbox."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from tallerclaro.application.dtos import CapturedPayment, PaymentIntent
from tallerclaro.application.ports import PaymentProcessor
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError


class UnconfiguredPaymentProcessor:
    """Doble por defecto cuando PayPal no está configurado."""

    def __init__(self, message: str = "Payment processor is not configured") -> None:
        self._message = message

    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


class FakePaymentProcessor:
    """Doble de prueba para simular pagos sin llamadas externas."""

    def __init__(self, success: bool = True) -> None:
        self._success = success
        self._created: dict[str, PaymentIntent] = {}

    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        paypal_order_id = f"PAYPAL-TEST-{len(self._created) + 1}"
        intent = PaymentIntent(
            payment_id=0,
            paypal_order_id=paypal_order_id,
            amount=Decimal(amount),  # type: ignore[name-defined]
            currency=currency,
            approval_url=None,
        )
        self._created[paypal_order_id] = intent
        return intent

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        if paypal_order_id not in self._created:
            raise DomainError(code="PAYMENT_NOT_FOUND", message="PayPal order not found")
        if not self._success:
            raise DomainError(code="PAYMENT_FAILED", message="Simulated PayPal capture failure")
        intent = self._created[paypal_order_id]
        return CapturedPayment(
            payment_id=0,
            status="completed",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=f"CAPTURE-{paypal_order_id}",
            amount=intent.amount,
            currency=intent.currency,
            paid_at=datetime.now(timezone.utc).isoformat(),
        )


class PayPalPaymentProcessor:
    """Adaptador de PayPal REST API v2."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(timeout=30.0)
        self._base_url = settings.paypal_api_base
        if self._base_url is None:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="PayPal mode is not configured")

    def create_order(self, amount: str, currency: str) -> PaymentIntent:
        access_token = self._get_access_token()
        response = self._client.post(
            f"{self._base_url}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {"currency_code": currency, "value": amount},
                    }
                ],
                "application_context": {
                    "return_url": "https://example.com/payment/return",
                    "cancel_url": "https://example.com/payment/cancel",
                },
            },
        )
        if response.status_code != 201:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal create order failed: {response.status_code}",
            )
        data = response.json()
        paypal_order_id = data["id"]
        approval_url = None
        for link in data.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link["href"]
                break
        return PaymentIntent(
            payment_id=0,
            paypal_order_id=paypal_order_id,
            amount=Decimal(amount),  # type: ignore[name-defined]
            currency=currency,
            approval_url=approval_url,
        )

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        access_token = self._get_access_token()
        response = self._client.post(
            f"{self._base_url}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        if response.status_code not in (200, 201):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal capture failed: {response.status_code}",
            )
        data = response.json()
        if data.get("status") != "COMPLETED":
            raise DomainError(
                code="PAYMENT_FAILED",
                message=f"PayPal order not completed: {data.get('status')}",
            )
        purchase_unit = data["purchase_units"][0]
        capture = purchase_unit["payments"]["captures"][0]
        return CapturedPayment(
            payment_id=0,
            status="completed",
            paypal_order_id=paypal_order_id,
            paypal_capture_id=capture["id"],
            amount=Decimal(capture["amount"]["value"]),  # type: ignore[name-defined]
            currency=capture["amount"]["currency_code"],
            paid_at=datetime.now(timezone.utc).isoformat(),
        )

    def _get_access_token(self) -> str:
        if not self._settings.paypal_client_id or not self._settings.paypal_client_secret:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="PayPal credentials missing")
        response = self._client.post(
            f"{self._base_url}/v1/oauth2/token",
            auth=(self._settings.paypal_client_id, self._settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal authentication failed: {response.status_code}",
            )
        return response.json()["access_token"]


def build_payment_processor(settings: Settings) -> PaymentProcessor:
    if settings.paypal_mode == "none" or not settings.paypal_mode:
        return UnconfiguredPaymentProcessor()
    if settings.paypal_mode in {"sandbox", "live"}:
        return PayPalPaymentProcessor(settings)
    return UnconfiguredPaymentProcessor(f"Unknown PayPal mode: {settings.paypal_mode}")
