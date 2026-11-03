"""Esquemas Pydantic para cotizaciones."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str
    email: EmailStr
    phone: str | None = None


class CreateQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    customer: CustomerInput
    carpenter_id: int
    request: str


class QuoteLineItemResponse(BaseModel):
    id: str
    type: str
    description: str
    unit: str
    quantity: float
    unit_amount: float
    amount: float


class QuoteResponse(BaseModel):
    id: str
    customer_id: str
    carpenter_id: str
    request: str
    description: str | None
    items: list[QuoteLineItemResponse]
    currency: str
    total: float | None
    deposit_amount: float | None
    balance_amount: float | None
    status: str
    customer_token: str | None = None
    assumptions: list[str] | None = None
    missing_info: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class GenerateQuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    additional_info: str | None = None


class QuoteGenerateResponse(BaseModel):
    id: str
    status: str
    description: str | None
    items: list[QuoteLineItemResponse]
    total: float | None
    assumptions: list[str] | None = None
    missing_info: list[str] | None = None
