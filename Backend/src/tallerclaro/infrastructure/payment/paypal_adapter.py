"""Adaptador de PayPal Sandbox."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

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
        try:
            data = response.json()
        except Exception as exc:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="Invalid JSON in PayPal capture response",
            ) from exc

        if not isinstance(data, dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="Malformed PayPal capture payload",
            )

        if data.get("status") != "COMPLETED":
            raise DomainError(
                code="PAYMENT_FAILED",
                message=f"PayPal order not completed: {data.get('status')}",
            )

        returned_order_id = str(data.get("id") or "").strip()
        if not returned_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing order id",
            )
        if returned_order_id != paypal_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture order id mismatch",
            )

        purchase_units = data.get("purchase_units")
        if not isinstance(purchase_units, list) or not purchase_units:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing purchase_units",
            )
        first_unit = purchase_units[0] if isinstance(purchase_units[0], dict) else {}
        payments_obj = first_unit.get("payments") if isinstance(first_unit.get("payments"), dict) else {}
        captures = payments_obj.get("captures")
        if not isinstance(captures, list) or not captures or not isinstance(captures[0], dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing captures",
            )

        capture = captures[0]
        capture_status = str(capture.get("status") or "").upper()
        if capture_status != "COMPLETED":
            raise DomainError(
                code="PAYMENT_FAILED",
                message=f"PayPal capture status is not COMPLETED: {capture.get('status')}",
            )

        capture_id = str(capture.get("id") or "").strip()
        if not capture_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing capture id",
            )

        amount_obj = capture.get("amount")
        if not isinstance(amount_obj, dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing amount",
            )
        raw_value = amount_obj.get("value")
        currency_code = str(amount_obj.get("currency_code") or "").strip()
        if raw_value is None or not currency_code:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture amount value or currency_code missing",
            )
        try:
            parsed_amount = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture amount is not a valid decimal",
            ) from exc

        raw_paid_at = str(capture.get("update_time") or capture.get("create_time") or "").strip()
        if raw_paid_at:
            if raw_paid_at.endswith("Z"):
                raw_paid_at = raw_paid_at[:-1] + "+00:00"
            paid_at = raw_paid_at
        else:
            paid_at = datetime.now(timezone.utc).isoformat()

        return CapturedPayment(
            payment_id=0,
            status="completed",
            paypal_order_id=returned_order_id,
            paypal_capture_id=capture_id,
            amount=parsed_amount,
            currency=currency_code,
            paid_at=paid_at,
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
