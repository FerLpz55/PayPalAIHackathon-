"""Router HTTP del asistente contable del taller."""

from __future__ import annotations

from fastapi import APIRouter

from tallerclaro.application.use_cases import AskAccountingAssistant, GetWorkshopFinancialSummary
from tallerclaro.domain.entities import CarpenterId
from tallerclaro.presentation.http.dependencies import (
    AccountingAssistantDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
)
from tallerclaro.presentation.http.mappers import (
    to_financial_summary_response as _to_summary_response,
)
from tallerclaro.presentation.http.schemas.accounting import (
    AccountingAnswerResponse,
    AccountingQuestionRequest,
    FinancialSummaryResponse,
)

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


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
