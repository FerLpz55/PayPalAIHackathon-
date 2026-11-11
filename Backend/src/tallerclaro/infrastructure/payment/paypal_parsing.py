"""Parsers puros de respuestas de la API REST de PayPal.

Estos colaboradores no conocen el cliente HTTP, la configuración ni la base de
datos: reciben el cuerpo ya decodificado y lo convierten en DTOs de aplicación,
lanzando ``DomainError`` cuando el contenido no cumple el contrato esperado.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from tallerclaro.application.dtos import (
    CapturedPayment,
    PaymentIntent,
    ProviderOrder,
    WebhookEvent,
)
from tallerclaro.domain.exceptions import DomainError


class PayPalOrderParser:
    """Convierte la respuesta de creación de una orden PayPal en ``PaymentIntent``."""

    @staticmethod
    def parse(data: object, amount: str, currency: str) -> PaymentIntent:
        if not isinstance(data, dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="Malformed PayPal create order payload",
            )

        paypal_order_id = str(data.get("id") or "").strip()
        if not paypal_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal create order response is missing order id",
            )

        return PaymentIntent(
            payment_id=0,
            paypal_order_id=paypal_order_id,
            amount=Decimal(amount),
            currency=currency,
            approval_url=PayPalOrderParser._extract_approval_url(data),
        )

    @staticmethod
    def _extract_approval_url(data: dict) -> str | None:
        links = data.get("links")
        if not isinstance(links, list):
            return None
        for link in links:
            if isinstance(link, dict) and link.get("rel") == "approve":
                href = link.get("href")
                return str(href) if href else None
        return None


class PayPalOrderStatusParser:
    """Convierte la respuesta de ``GET /v2/checkout/orders/{id}`` en ``ProviderOrder``.

    No captura ni escribe: solo informa el estado actual. Si la orden ya está
    ``COMPLETED``, extrae la captura completada para que el caso de uso pueda
    persistirla sin volver a capturar.
    """

    @staticmethod
    def parse(data: object, expected_order_id: str) -> ProviderOrder:
        if not isinstance(data, dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="Malformed PayPal get order payload",
            )

        returned_order_id = str(data.get("id") or "").strip()
        if not returned_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal get order response is missing order id",
            )
        if returned_order_id != expected_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal get order id mismatch",
            )

        status = str(data.get("status") or "").strip().upper()
        if not status:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal get order response is missing status",
            )

        capture = None
        if status == "COMPLETED":
            capture = PayPalCaptureParser.parse(data, expected_order_id)

        return ProviderOrder(
            paypal_order_id=returned_order_id,
            status=status,
            approval_url=PayPalOrderParser._extract_approval_url(data),
            capture=capture,
        )


class PayPalCaptureParser:
    """Valida la respuesta de captura y extrae el pago confirmado."""

    @staticmethod
    def parse(data: object, expected_order_id: str) -> CapturedPayment:
        if not isinstance(data, dict):
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="Malformed PayPal capture payload",
            )

        returned_order_id = PayPalCaptureParser._require_completed_order_id(
            data, expected_order_id
        )
        capture, capture_id = PayPalCaptureParser._extract_completed_capture(data)
        parsed_amount, currency_code = PayPalCaptureParser._extract_capture_amount(capture)

        return CapturedPayment(
            payment_id=0,
            status="completed",
            paypal_order_id=returned_order_id,
            paypal_capture_id=capture_id,
            amount=parsed_amount,
            currency=currency_code,
            paid_at=PayPalCaptureParser._parse_paid_at(capture),
        )

    @staticmethod
    def _require_completed_order_id(data: dict, expected_order_id: str) -> str:
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
        if returned_order_id != expected_order_id:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture order id mismatch",
            )
        return returned_order_id

    @staticmethod
    def _extract_completed_capture(data: dict) -> tuple[dict, str]:
        purchase_units = data.get("purchase_units")
        if not isinstance(purchase_units, list) or not purchase_units:
            raise DomainError(
                code="PAYMENT_PROVIDER_ERROR",
                message="PayPal capture response is missing purchase_units",
            )

        first_unit = purchase_units[0] if isinstance(purchase_units[0], dict) else {}
        payments_obj = (
            first_unit.get("payments") if isinstance(first_unit.get("payments"), dict) else {}
        )
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
        return capture, capture_id

    @staticmethod
    def _extract_capture_amount(capture: dict) -> tuple[Decimal, str]:
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

        return parsed_amount, currency_code

    @staticmethod
    def _parse_paid_at(capture: dict) -> str:
        raw_paid_at = str(capture.get("update_time") or capture.get("create_time") or "").strip()
        if not raw_paid_at:
            return datetime.now(timezone.utc).isoformat()
        if raw_paid_at.endswith("Z"):
            return raw_paid_at[:-1] + "+00:00"
        return raw_paid_at


class PayPalWebhookParser:
    """Reduce un evento de PayPal verificado a ``WebhookEvent``.

    Solo extrae identificadores y, si el evento trae una captura completada, el
    DTO con importe y moneda para contrastarlo en la capa de aplicación.
    """

    _CAPTURE_COMPLETED_EVENTS = {
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.PENDING",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.REFUNDED",
        "PAYMENT.CAPTURE.REVERSED",
    }

    @classmethod
    def parse(cls, data: object) -> WebhookEvent:
        if not isinstance(data, dict):
            raise DomainError(
                code="VALIDATION_ERROR",
                message="Malformed PayPal webhook payload",
            )

        event_id = str(data.get("id") or "").strip()
        event_type = str(data.get("event_type") or "").strip().upper()
        if not event_id or not event_type:
            raise DomainError(
                code="VALIDATION_ERROR",
                message="PayPal webhook payload is missing id or event_type",
            )

        resource = data.get("resource") if isinstance(data.get("resource"), dict) else {}
        if event_type in cls._CAPTURE_COMPLETED_EVENTS:
            return cls._parse_capture_event(event_id, event_type, resource)

        order_id = str(resource.get("id") or "").strip()
        return WebhookEvent(
            id=event_id,
            type=event_type,
            paypal_order_id=order_id or None,
            summary=event_type,
        )

    @classmethod
    def _parse_capture_event(
        cls, event_id: str, event_type: str, resource: dict
    ) -> WebhookEvent:
        order_id = cls._related_order_id(resource)
        capture = None
        if (
            event_type == "PAYMENT.CAPTURE.COMPLETED"
            and str(resource.get("status") or "").upper() == "COMPLETED"
        ):
            capture_id = str(resource.get("id") or "").strip()
            amount, currency = PayPalCaptureParser._extract_capture_amount(resource)
            if not capture_id:
                raise DomainError(
                    code="PAYMENT_PROVIDER_ERROR",
                    message="PayPal webhook capture is missing id",
                )
            capture = CapturedPayment(
                payment_id=0,
                status="completed",
                paypal_order_id=order_id or "",
                paypal_capture_id=capture_id,
                amount=amount,
                currency=currency,
                paid_at=PayPalCaptureParser._parse_paid_at(resource),
            )
        return WebhookEvent(
            id=event_id,
            type=event_type,
            paypal_order_id=order_id,
            capture=capture,
            summary=event_type,
        )

    @staticmethod
    def _related_order_id(resource: dict) -> str | None:
        supplementary = (
            resource.get("supplementary_data")
            if isinstance(resource.get("supplementary_data"), dict)
            else {}
        )
        related = (
            supplementary.get("related_ids")
            if isinstance(supplementary.get("related_ids"), dict)
            else {}
        )
        order_id = str(related.get("order_id") or "").strip()
        return order_id or None
