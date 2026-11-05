"""Router HTTP del asistente contable del taller."""

from __future__ import annotations

from fastapi import APIRouter

from tallerclaro.application.use_cases import AskAccountingAssistant, GetWorkshopFinancialSummary
from tallerclaro.domain.accounting import WorkshopFinancialSummary
from tallerclaro.domain.entities import CarpenterId
from tallerclaro.presentation.http.dependencies import (
    AccountingAssistantDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
)
from tallerclaro.presentation.http.schemas.accounting import (
    AccountingAnswerResponse,
    AccountingQuestionRequest,
    FinancialSummaryResponse,
)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


def _to_summary_response(summary: WorkshopFinancialSummary) -> FinancialSummaryResponse:
    return FinancialSummaryResponse(
        currency=summary.currency,
        orders_count=summary.orders_count,
        active_orders_count=summary.active_orders_count,
        delivered_orders_count=summary.delivered_orders_count,
        orders_awaiting_deposit=summary.orders_awaiting_deposit,
        orders_with_balance_due=summary.orders_with_balance_due,
        total_contracted=float(summary.total_contracted.amount),
        collected_total=float(summary.collected_total.amount),
        collected_deposits=float(summary.collected_deposits.amount),
        collected_balances=float(summary.collected_balances.amount),
        pending_to_collect=float(summary.pending_to_collect.amount),
        average_order_value=float(summary.average_order_value.amount),
    )


@router.get("/summary")
def get_financial_summary(
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
) -> FinancialSummaryResponse:
    summary = GetWorkshopFinancialSummary(uow).execute(CarpenterId(principal.carpenter_id))
    return _to_summary_response(summary)


@router.post("/assistant")
def ask_accounting_assistant(
    payload: AccountingQuestionRequest,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
    assistant: AccountingAssistantDep,
) -> AccountingAnswerResponse:
    result = AskAccountingAssistant(uow, assistant).execute(
        CarpenterId(principal.carpenter_id), payload.question
    )
    return AccountingAnswerResponse(
        question=result.question,
        answer=result.answer,
        summary=_to_summary_response(result.summary),
    )
