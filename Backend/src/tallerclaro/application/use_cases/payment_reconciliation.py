"""Webhooks de PayPal y conciliación periódica de pagos.

Ambos casos reutilizan ``SyncPayment`` para que la única fuente de verdad sea
una consulta a PayPal: un webhook nunca acredita un pago con datos del cuerpo
sin verificarlos. Ninguna llamada de red se ejecuta dentro de una transacción.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from tallerclaro.application.dtos import WebhookEvent
from tallerclaro.application.exceptions import DomainError
from tallerclaro.application.interfaces import PaymentProcessor, UnitOfWork, WebhookVerifier
from tallerclaro.application.use_cases.payments import SyncPayment
from tallerclaro.domain.entities import PAYMENT_STATUS_COMPLETED

logger = logging.getLogger(__name__)

# Eventos que pueden cambiar el estado local de un pago. Cualquier otro se
# registra como ignorado: los reembolsos y disputas quedan fuera de este
# release y requieren resolución manual.
RECONCILABLE_EVENT_TYPES = frozenset(
    {
        "CHECKOUT.ORDER.APPROVED",
        "CHECKOUT.ORDER.COMPLETED",
        "CHECKOUT.ORDER.VOIDED",
        "PAYMENT.CAPTURE.COMPLETED",
        "PAYMENT.CAPTURE.PENDING",
        "PAYMENT.CAPTURE.DENIED",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HandlePayPalWebhook:
    """Verifica, deduplica y concilia un evento de PayPal.

    Orden: (1) verificar la firma fuera de SQL; (2) reclamar el evento de forma
    atómica para que una reentrega no se procese dos veces; (3) conciliar con
    ``SyncPayment`` consultando a PayPal; (4) marcar el resultado. Un fallo deja
    el evento como ``failed`` para que la siguiente entrega pueda reintentarlo.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        verifier: WebhookVerifier,
        payment_processor: PaymentProcessor,
    ) -> None:
        self._uow = uow
        self._verifier = verifier
        self._payment_processor = payment_processor

    def execute(self, headers: dict[str, str], body: bytes) -> str:
        event = self._verifier.verify(headers, body)
        claim = self._uow.execute_sql(lambda uow: uow.paypal_events.claim(event))
        if claim == "duplicate":
            return "duplicate"

        try:
            outcome, detail = self._reconcile(event)
        except DomainError as exc:
            self._mark(event.id, "failed", f"{exc.code}: {exc.message}")
            raise
        except Exception:
            self._mark(event.id, "failed", "Unexpected error while reconciling")
            raise

        self._mark(event.id, outcome, detail)
        return outcome

    def _mark(self, event_id: str, outcome: str, detail: str | None) -> None:
        self._uow.execute_sql(
            lambda uow: uow.paypal_events.mark_processed(event_id, outcome, detail)
        )

    def _reconcile(self, event: WebhookEvent) -> tuple[str, str]:
        if event.type not in RECONCILABLE_EVENT_TYPES:
            return "ignored", f"Event {event.type} is outside this release"
        if not event.paypal_order_id:
            return "ignored", "Event does not reference a PayPal order"

        with self._uow:
            payment = self._uow.payments.get_by_paypal_order_id(event.paypal_order_id)
            payment_id = payment.id if payment is not None else None
            status = payment.status if payment is not None else None

        if payment_id is None:
            return "ignored", "Unknown PayPal order"
        if status == PAYMENT_STATUS_COMPLETED:
            return "processed", "Payment was already completed"

        synced = SyncPayment(self._uow, self._payment_processor).execute(payment_id)
        return "processed", f"Payment reconciled to {synced.status}"


class ReconcileStalePayments:
    """Conciliación periódica de intentos pendientes sin actividad reciente.

    Se ejecuta fuera del ciclo de petición y abre una unidad de trabajo por pago,
    igual que una petición normal. Un error en un pago no detiene el lote.
    """

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        payment_processor: PaymentProcessor,
        min_age_seconds: int = 300,
        batch_size: int = 20,
    ) -> None:
        self._uow_factory = uow_factory
        self._payment_processor = payment_processor
        self._min_age_seconds = min_age_seconds
        self._batch_size = batch_size

    def execute(self) -> dict[str, int]:
        cutoff = _utcnow() - timedelta(seconds=self._min_age_seconds)
        with self._uow_factory() as uow:
            stale = uow.payments.list_stale_pending(cutoff, self._batch_size)

        results = {
            "checked": 0,
            "completed": 0,
            "cancelled": 0,
            "pending": 0,
            "failed": 0,
        }
        for payment in stale:
            results["checked"] += 1
            try:
                synced = SyncPayment(
                    self._uow_factory(), self._payment_processor
                ).execute(payment.id)
            except Exception:
                # Un fallo de transporte deja la reserva intacta; se reintenta en
                # la siguiente pasada sin abortar el resto del lote.
                logger.warning(
                    "Payment reconciliation failed for payment %s", payment.id,
                    exc_info=True,
                )
                results["failed"] += 1
                continue

            if synced.status == PAYMENT_STATUS_COMPLETED:
                results["completed"] += 1
            elif synced.status == "cancelled":
                results["cancelled"] += 1
            else:
                results["pending"] += 1
        return results
