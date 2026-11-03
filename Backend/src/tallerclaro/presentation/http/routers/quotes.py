"""Router HTTP para cotizaciones."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from tallerclaro.application.dtos import CreateQuoteInput, CustomerInput
from tallerclaro.application.use_cases import (
    ApproveQuote,
    CreateQuote,
    GenerateQuoteProposal,
    GetQuote,
    RejectQuote,
)
from tallerclaro.domain.entities import QuoteId
from tallerclaro.presentation.http.dependencies import (
    PrincipalDep,
    UnitOfWorkDep,
    WorkshopCarpenterDep,
    get_unit_of_work,
    require_quote_or_workshop_principal,
    require_workshop_credentials,
)
from tallerclaro.presentation.http.schemas.quotes import (
    CreateQuoteRequest,
    GenerateQuoteRequest,
    QuoteGenerateResponse,
    QuoteLineItemResponse,
    QuoteResponse,
)

router = APIRouter(prefix="/api", tags=["quotes"])


def _to_line_item_response(item):
    return QuoteLineItemResponse(
        id=str(item.id) if item.id is not None else "",
        type=item.type,
        description=item.description,
        unit=item.unit,
        quantity=float(item.quantity),
        unit_amount=float(item.unit_price.amount),
        amount=float(item.amount.amount),
    )


def _to_quote_response(quote, include_missing: bool = False, customer_token: str | None = None) -> QuoteResponse:
    deposit = float(quote.deposit_amount.amount) if quote.deposit_amount is not None else None
    balance = float(quote.balance_amount.amount) if quote.balance_amount is not None else None
    return QuoteResponse(
        id=str(quote.id) if quote.id is not None else "",
        customer_id=str(quote.customer_id),
        carpenter_id=str(quote.carpenter_id),
        request=quote.request,
        description=quote.description,
        items=[_to_line_item_response(item) for item in quote.line_items],
        currency=quote.currency,
        total=float(quote.total.amount) if quote.total is not None else None,
        deposit_amount=deposit,
        balance_amount=balance,
        status=quote.status,
        customer_token=customer_token,
        assumptions=list(quote.assumptions) if quote.assumptions else None,
        missing_info=list(quote.missing_info) if quote.missing_info is not None else ([] if include_missing else None),
        created_at=quote.created_at.isoformat() if quote.created_at else None,
        updated_at=quote.updated_at.isoformat() if quote.updated_at else None,
    )


@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: CreateQuoteRequest,
    uow: UnitOfWorkDep,
) -> QuoteResponse:
    use_case = CreateQuote(uow)
    result = use_case.execute(
        CreateQuoteInput(
            customer=CustomerInput(
                name=payload.customer.name,
                email=payload.customer.email,
                phone=payload.customer.phone,
            ),
            carpenter_id=payload.carpenter_id,
            request=payload.request,
        )
    )
    return _to_quote_response(result.quote, customer_token=result.customer_token)


@router.get("/quotes/{quote_id}")
def get_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
) -> QuoteResponse:
    use_case = GetQuote(uow)
    quote = use_case.execute(QuoteId(quote_id), principal)
    return _to_quote_response(quote)


@router.post("/quotes/{quote_id}/generate")
def generate_quote(
    quote_id: int,
    request: Request,
    principal: WorkshopCarpenterDep,
    uow: UnitOfWorkDep,
    body: GenerateQuoteRequest | None = None,
) -> QuoteGenerateResponse:
    ai_service = request.app.state.ai_service
    use_case = GenerateQuoteProposal(uow, ai_service)
    additional_info = body.additional_info if body is not None else None
    quote = use_case.execute(
        QuoteId(quote_id),
        additional_info=additional_info,
        principal=principal,
    )
    return QuoteGenerateResponse(
        id=str(quote.id) if quote.id is not None else "",
        status=quote.status,
        description=quote.description,
        items=[_to_line_item_response(item) for item in quote.line_items],
        total=float(quote.total.amount) if quote.total is not None else None,
        assumptions=list(quote.assumptions) if quote.assumptions else None,
        missing_info=list(quote.missing_info) if quote.status == "needs_information" else None,
    )


@router.post("/quotes/{quote_id}/approve")
def approve_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
):
    from tallerclaro.presentation.http.schemas.orders import OrderResponse

    use_case = ApproveQuote(uow)
    order = use_case.execute(QuoteId(quote_id), principal)
    return OrderResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.balance_amount.amount),
        currency=order.currency,
        status=order.status,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
    )


@router.post("/quotes/{quote_id}/reject")
def reject_quote(
    quote_id: int,
    principal: PrincipalDep,
    uow: UnitOfWorkDep,
) -> QuoteResponse:
    use_case = RejectQuote(uow)
    quote = use_case.execute(QuoteId(quote_id), principal)
    return _to_quote_response(quote)
