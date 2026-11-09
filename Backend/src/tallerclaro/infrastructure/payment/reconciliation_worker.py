"""Bucle de conciliación de pagos en segundo plano.

El trabajo pesado (SQL + consultas a PayPal) es síncrono y se ejecuta en un hilo
para no bloquear el event loop. Un fallo en una pasada se registra y se
reintenta en la siguiente; cancelar la tarea detiene el bucle de inmediato.
"""

from __future__ import annotations

import asyncio
import logging

from tallerclaro.application.use_cases import ReconcileStalePayments

logger = logging.getLogger(__name__)


class PaymentReconciliationWorker:
    def __init__(
        self,
        use_case: ReconcileStalePayments,
        interval_seconds: int,
    ) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be at least 1")
        self._use_case = use_case
        self._interval_seconds = interval_seconds

    async def run(self) -> None:
        logger.info(
            "Payment reconciliation worker started (every %ss)",
            self._interval_seconds,
        )
        while True:
            try:
                await asyncio.to_thread(self._use_case.execute)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Payment reconciliation pass failed")
            await asyncio.sleep(self._interval_seconds)
