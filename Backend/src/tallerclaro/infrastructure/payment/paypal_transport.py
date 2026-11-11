"""Transporte HTTP de la API REST de PayPal.

Encapsula las peticiones y la autenticación OAuth. Devuelve el código de
estado y el cuerpo decodificado; no interpreta reglas de negocio ni valida la
estructura de las respuestas (eso corresponde a ``paypal_parsing``).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError


@dataclass(frozen=True)
class PayPalResponse:
    status_code: int
    payload: object | None


class PayPalHttpTransport:
    """Cliente HTTP mínimo para crear, consultar y capturar órdenes PayPal."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=30.0)
        self._base_url = settings.paypal_api_base
        self._client_id = settings.paypal_client_id
        self._client_secret = settings.paypal_client_secret
        if self._base_url is None:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="PayPal mode is not configured")

    def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return getattr(self._client, method)(url, **kwargs)
        except httpx.RequestError:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal transport unavailable; retry the same payment",
            ) from None

    def create_order(
        self,
        amount: str,
        currency: str,
        return_url: str | None,
        cancel_url: str | None,
        access_token: str,
        request_id: str | None = None,
        brand_name: str | None = None,
    ) -> PayPalResponse:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if request_id:
            # PayPal deduplica por esta clave: reintentar el mismo intento no
            # debe crear una segunda orden.
            headers["PayPal-Request-Id"] = request_id
        application_context = {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
        }
        if brand_name:
            application_context["brand_name"] = brand_name
        response = self._send(
            "post",
            f"{self._base_url}/v2/checkout/orders",
            headers=headers,
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {"currency_code": currency, "value": amount},
                    }
                ],
                "application_context": application_context,
            },
        )
        return self._to_response(response)

    def capture_order(
        self, paypal_order_id: str, request_id: str, access_token: str
    ) -> PayPalResponse:
        response = self._send(
            "post",
            f"{self._base_url}/v2/checkout/orders/{paypal_order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
                "PayPal-Request-Id": request_id,
            },
        )
        return self._to_response(response)

    def get_order(self, paypal_order_id: str, access_token: str) -> PayPalResponse:
        response = self._send(
            "get",
            f"{self._base_url}/v2/checkout/orders/{paypal_order_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return self._to_response(response)

    def verify_webhook_signature(
        self, verification: dict, access_token: str
    ) -> PayPalResponse:
        response = self._send(
            "post",
            f"{self._base_url}/v1/notifications/verify-webhook-signature",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=verification,
        )
        return self._to_response(response)

    def access_token(self) -> str:
        if not self._client_id or not self._client_secret:
            raise DomainError(code="SERVICE_UNAVAILABLE", message="PayPal credentials missing")
        response = self._send(
            "post",
            f"{self._base_url}/v1/oauth2/token",
            auth=(self._client_id, self._client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal authentication failed: {response.status_code}",
            )
        payload = self._json(response)
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal authentication response is missing access token",
            )
        return token

    @staticmethod
    def _to_response(response: httpx.Response) -> PayPalResponse:
        return PayPalResponse(status_code=response.status_code, payload=PayPalHttpTransport._json(response))

    @staticmethod
    def _json(response: httpx.Response) -> object | None:
        try:
            return response.json()
        except Exception:
            return None
