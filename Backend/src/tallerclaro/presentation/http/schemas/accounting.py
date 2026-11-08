"""Esquemas Pydantic del asistente contable."""

from pydantic import BaseModel, Field


class FinancialSummaryResponse(BaseModel):
    currency: str
    orders_count: int
    active_orders_count: int
    delivered_orders_count: int
    orders_awaiting_deposit: int
    orders_with_balance_due: int
    total_contracted: float
    collected_total: float
    collected_deposits: float
    collected_balances: float
    pending_to_collect: float
    average_order_value: float


class AccountingQuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AccountingAnswerResponse(BaseModel):
    question: str
    answer: str
    summary: FinancialSummaryResponse

