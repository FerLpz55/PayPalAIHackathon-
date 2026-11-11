"""Verificación de webhooks de PayPal.

PayPal firma cada entrega con cabeceras ``PAYPAL-TRANSMISSION-*``. El backend
nunca confía en el cuerpo: llama a la API oficial de verificación y solo
procesa el evento si PayPal responde ``SUCCESS``. El transporte HTTP vive en
``paypal_transport`` y la reducción del evento en ``paypal_parsing``.
"""

from __future__ import annotations

import json

from tallerclaro.application.dtos import WebhookEvent
from tallerclaro.application.interfaces import WebhookVerifier
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_parsing import PayPalWebhookParser
from tallerclaro.infrastructure.payment.paypal_transport import (
    PayPalHttpTransport,
    PayPalResponse,
)

_REQUIRED_HEADERS = (
    "paypal-transmission-id",
    "paypal-transmission-time",
    "paypal-transmission-sig",
    "paypal-cert-url",
    "paypal-auth-algo",
)


class PayPalWebhookVerifier(WebhookVerifier):
    """Verifica la firma contra la API de PayPal y normaliza el evento."""

    def __init__(self, settings: Settings, transport: PayPalHttpTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport or PayPalHttpTransport(settings)

    def verify(self, headers: dict[str, str], body: bytes) -> WebhookEvent:
        if not self._settings.paypal_webhook_id:
            raise DomainError(
                code="SERVICE_UNAVAILABLE",
                message="PayPal webhook verification is not configured",
            )

        normalized = {key.lower(): value for key, value in headers.items()}
        missing = [name for name in _REQUIRED_HEADERS if not normalized.get(name)]
        if missing:
            raise DomainError(
                code="UNAUTHORIZED",
                message="PayPal webhook signature headers are missing",
            )

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DomainError(
                code="VALIDATION_ERROR",
                message="PayPal webhook body is not valid JSON",
            ) from exc
        if not isinstance(payload, dict):
            raise DomainError(
                code="VALIDATION_ERROR",
                message="PayPal webhook body must be a JSON object",
            )

        verification = {
            "auth_algo": normalized["paypal-auth-algo"],
            "cert_url": normalized["paypal-cert-url"],
            "transmission_id": normalized["paypal-transmission-id"],
            "transmission_sig": normalized["paypal-transmission-sig"],
            "transmission_time": normalized["paypal-transmission-time"],
            "webhook_id": self._settings.paypal_webhook_id,
            "webhook_event": payload,
        }
        access_token = self._transport.access_token()
        response = self._transport.verify_webhook_signature(verification, access_token)
        self._require_success(response)
        return PayPalWebhookParser.parse(payload)

    @staticmethod
    def _require_success(response: PayPalResponse) -> None:
        if response.status_code != 200:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal webhook verification failed: {response.status_code}",
            )
        payload = response.payload if isinstance(response.payload, dict) else {}
        if str(payload.get("verification_status") or "").upper() != "SUCCESS":
            raise DomainError(
                code="UNAUTHORIZED",
                message="PayPal webhook signature was not verified",
            )


class UnconfiguredWebhookVerifier(WebhookVerifier):
    """Rechaza cualquier webhook cuando PayPal no está configurado."""

    def __init__(self, message: str = "PayPal webhooks are not configured") -> None:
        self._message = message

    def verify(self, headers: dict[str, str], body: bytes) -> WebhookEvent:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


def build_webhook_verifier(settings: Settings) -> WebhookVerifier:
    mode = (settings.paypal_mode or "").lower().strip()
    if mode not in {"sandbox", "live"} or not settings.paypal_webhook_id:
        return UnconfiguredWebhookVerifier()
    return PayPalWebhookVerifier(settings)
