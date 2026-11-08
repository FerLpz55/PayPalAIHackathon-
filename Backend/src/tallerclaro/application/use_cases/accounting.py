"""Casos de uso del asistente contable del taller."""

from __future__ import annotations

from tallerclaro.application.dtos import AccountingAnswer
from tallerclaro.application.exceptions import DomainError, ValidationDomainError
from tallerclaro.application.interfaces import AccountingAssistant, UnitOfWork
from tallerclaro.domain.accounting import WorkshopFinancialSummary, summarize_workshop_finances
from tallerclaro.domain.entities import CarpenterId, Order, OrderId, Payment

ORDERS_PAGE_SIZE = 100
MAX_ORDERS_IN_SUMMARY = 1000
QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500
ANSWER_MAX_LENGTH = 1500


def _load_summary(uow: UnitOfWork, carpenter_id: CarpenterId) -> WorkshopFinancialSummary:
    """Lee pedidos y pagos del taller dentro de una transacción ya abierta."""

    orders: list[Order] = []
    offset = 0
    while len(orders) < MAX_ORDERS_IN_SUMMARY:
        page = uow.orders.list_by_carpenter(carpenter_id, ORDERS_PAGE_SIZE, offset)
        orders.extend(page)
        if len(page) < ORDERS_PAGE_SIZE:
            break
        offset += ORDERS_PAGE_SIZE
    orders = orders[:MAX_ORDERS_IN_SUMMARY]

    payments_by_order: dict[OrderId, list[Payment]] = {
        order.id: uow.payments.list_by_order(order.id)
        for order in orders
        if order.id is not None
    }
    return summarize_workshop_finances(orders, payments_by_order)


class GetWorkshopFinancialSummary:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, carpenter_id: CarpenterId) -> WorkshopFinancialSummary:
        with self._uow:
            return _load_summary(self._uow, carpenter_id)


class AskAccountingAssistant:
    """Responde preguntas del taller sobre sus cuentas.

    Fase 1: calcula el resumen dentro de la transacción y la cierra.
    Fase 2: consulta al asistente de IA fuera de la transacción.
    No hay fase de escritura: el caso de uso es de solo lectura.
    """

    def __init__(self, uow: UnitOfWork, assistant: AccountingAssistant) -> None:
        self._uow = uow
        self._assistant = assistant

    def execute(self, carpenter_id: CarpenterId, question: str) -> AccountingAnswer:
        cleaned = (question or "").strip()
        if len(cleaned) < QUESTION_MIN_LENGTH:
            raise ValidationDomainError("Question is too short", field="question")
        if len(cleaned) > QUESTION_MAX_LENGTH:
            raise ValidationDomainError(
                f"Question cannot exceed {QUESTION_MAX_LENGTH} characters", field="question"
            )

        with self._uow:
            summary = _load_summary(self._uow, carpenter_id)

        answer = (self._assistant.explain(summary, cleaned) or "").strip()
        if not answer:
            raise DomainError(code="AI_RESPONSE_INVALID", message="AI returned an empty answer")

        return AccountingAnswer(
            question=cleaned,
            answer=answer[:ANSWER_MAX_LENGTH],
            summary=summary,
        )

