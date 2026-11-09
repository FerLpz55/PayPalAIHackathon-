"""Procesador de pagos PayPal.

Coordina la creación y captura de órdenes delegando el transporte HTTP en
``paypal_transport`` y la validación de respuestas en ``paypal_parsing``.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
from urllib.parse import urlsplit

import httpx

from tallerclaro.application.dtos import CapturedPayment, PaymentIntent, ProviderOrder
from tallerclaro.application.interfaces import PaymentProcessor
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import DomainError
from tallerclaro.infrastructure.payment.paypal_parsing import (
    PayPalCaptureParser,
    PayPalOrderParser,
    PayPalOrderStatusParser,
)
from tallerclaro.infrastructure.payment.paypal_transport import (
    PayPalHttpTransport,
    PayPalResponse,
)


class UnconfiguredPaymentProcessor:
    """Implementación por defecto cuando el procesador de pagos no está configurado."""

    def __init__(self, message: str = "Payment processor is not configured") -> None:
        self._message = message

    def create_order(
        self, amount: str, currency: str, request_id: str | None = None
    ) -> PaymentIntent:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)

    def get_order(self, paypal_order_id: str) -> ProviderOrder:
        raise DomainError(code="SERVICE_UNAVAILABLE", message=self._message)


class PayPalPaymentProcessor:
    """Fachada de pagos PayPal para la capa de aplicación."""

    def __init__(
        self,
        settings: Settings,
        client: httpx.Client | None = None,
        transport: PayPalHttpTransport | None = None,
        order_parser: PayPalOrderParser | None = None,
        capture_parser: PayPalCaptureParser | None = None,
        status_parser: PayPalOrderStatusParser | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport or PayPalHttpTransport(settings, client=client)
        self._order_parser = order_parser or PayPalOrderParser()
        self._capture_parser = capture_parser or PayPalCaptureParser()
        self._status_parser = status_parser or PayPalOrderStatusParser()
        for name, url in (("return", settings.paypal_return_url), ("cancel", settings.paypal_cancel_url)):
            parts = urlsplit(url or "")
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise DomainError(code="SERVICE_UNAVAILABLE", message=f"PayPal {name} URL must be an HTTPS URL")

    def create_order(
        self, amount: str, currency: str, request_id: str | None = None
    ) -> PaymentIntent:
        access_token = self._transport.access_token()
        response = self._transport.create_order(
            amount=amount,
            currency=currency,
            return_url=self._settings.paypal_return_url,
            cancel_url=self._settings.paypal_cancel_url,
            access_token=access_token,
            request_id=request_id or self._new_request_id(),
            brand_name=self._settings.paypal_brand_name,
        )
        if response.status_code != 201:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal create order failed: {response.status_code}",
            )
        return self._order_parser.parse(self._require_payload(
            response, "Invalid JSON in PayPal create order response"
        ), amount, currency)

    def capture_order(self, paypal_order_id: str) -> CapturedPayment:
        access_token = self._transport.access_token()
        response = self._transport.capture_order(
            paypal_order_id=paypal_order_id,
            request_id=self._request_id(paypal_order_id),
            access_token=access_token,
        )
        if response.status_code not in (200, 201):
            response = self._transport.get_order(paypal_order_id, access_token=access_token)
            if response.status_code != 200:
                raise DomainError(
                    code="PAYMENT_PROVIDER_ERROR",
                    message="PayPal capture outcome is uncertain; retry reconciliation",
                )
        return self._capture_parser.parse(
            self._require_payload(response, "Invalid JSON in PayPal capture response"),
            paypal_order_id,
        )

    def get_order(self, paypal_order_id: str) -> ProviderOrder:
        access_token = self._transport.access_token()
        response = self._transport.get_order(paypal_order_id, access_token=access_token)
        if response.status_code != 200:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message=f"PayPal get order failed: {response.status_code}",
            )
        return self._status_parser.parse(
            self._require_payload(response, "Invalid JSON in PayPal get order response"),
            paypal_order_id,
        )

    @staticmethod
    def _require_payload(response: PayPalResponse, message: str) -> object:
        if response.payload is None:
            raise DomainError(code="PAYMENT_PROVIDER_ERROR", message=message)
        return response.payload

    @staticmethod
    def _request_id(paypal_order_id: str) -> str:
        return hashlib.sha256(paypal_order_id.encode()).hexdigest()[:36]

    @staticmethod
    def _new_request_id() -> str:
        import uuid

        return str(uuid.uuid4())


# Registro extensible de modos de procesador de pago (Open/Closed Principle).
_PAYMENT_PROCESSOR_FACTORIES: dict[str, Callable[[Settings], PaymentProcessor]] = {
    "sandbox": lambda s: PayPalPaymentProcessor(s),
    "live": lambda s: PayPalPaymentProcessor(s),
}


def register_payment_processor(
    mode: str, factory: Callable[[Settings], PaymentProcessor]
) -> None:
    """Registra una implementación para un modo sin modificar los casos de uso."""
    _PAYMENT_PROCESSOR_FACTORIES[mode.lower().strip()] = factory


def build_payment_processor(settings: Settings) -> PaymentProcessor:
    mode = (settings.paypal_mode or "").lower().strip()
    if not mode or mode == "none":
        return UnconfiguredPaymentProcessor()

    factory = _PAYMENT_PROCESSOR_FACTORIES.get(mode)
    if factory is not None:
        return factory(settings)

    return UnconfiguredPaymentProcessor(f"Unknown PayPal mode: {settings.paypal_mode}")
