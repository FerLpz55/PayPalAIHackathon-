"""Casos de uso para cotizaciones."""

from __future__ import annotations

import uuid

from tallerclaro.application.dtos import (
    AccessPrincipal,
    CreatedQuoteResult,
    CreateQuoteInput,
    CustomerInput,
    QuoteLineItemInput,
    QuoteProposalResult,
)
from tallerclaro.application.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationDomainError,
)
from tallerclaro.application.ports import AIService, UnitOfWork
from tallerclaro.domain.entities import (
    DEPOSIT_PERCENTAGE,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_APPROVED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_NEEDS_INFORMATION,
    QUOTE_STATUS_PENDING_REVIEW,
    Customer,
    Money,
    Order,
    Quote,
    QuoteId,
    QuoteLineItem,
)


def _authorize_quote_access(quote: Quote, principal: AccessPrincipal | None) -> None:
    if principal is None:
        return
    if principal.is_workshop:
        if principal.carpenter_id is not None and quote.carpenter_id != principal.carpenter_id:
            raise ForbiddenError("Not authorized to access this quote")
    elif principal.is_customer:
        if principal.quote_id != quote.id:
            raise ForbiddenError("Not authorized to access this quote")
    else:
        raise ForbiddenError("Invalid principal")



class CreateQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, input: CreateQuoteInput) -> CreatedQuoteResult:
        with self._uow:
            carpenter = self._uow.carpenters.get_by_id(input.carpenter_id)
            if carpenter is None:
                raise NotFoundError("Carpenter", input.carpenter_id)
            customer_input = input.customer
            normalized_name = customer_input.name.strip()
            normalized_email = customer_input.email.strip().lower()
            normalized_phone = (customer_input.phone.strip() or None) if customer_input.phone else None
            customer = Customer(
                id=None,
                name=normalized_name,
                email=normalized_email,
                phone=normalized_phone,
            )
            customer = self._uow.customers.save(customer)
            quote = Quote(
                id=None,
                customer_id=customer.id,
                carpenter_id=input.carpenter_id,
                request=input.request,
                description=None,
                line_items=[],
                total=None,
                status=QUOTE_STATUS_DRAFT,
            )
            quote = self._uow.quotes.save(quote)
            customer_token = self._uow.tokens.create(customer.id, quote.id)
            self._uow.commit()
            return CreatedQuoteResult(quote=quote, customer_token=customer_token)


class GetQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId, principal: AccessPrincipal | None = None) -> Quote:

        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            _authorize_quote_access(quote, principal)
            return quote


class GenerateQuoteProposal:
    def __init__(self, uow: UnitOfWork, ai_service: AIService) -> None:
        self._uow = uow
        self._ai_service = ai_service

    def execute(self, quote_id: QuoteId, additional_info: str | None = None) -> Quote:
        valid_statuses = {
            QUOTE_STATUS_DRAFT,
            QUOTE_STATUS_NEEDS_INFORMATION,
            QUOTE_STATUS_PENDING_REVIEW,
        }
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            if quote.status not in valid_statuses:
                raise ConflictError(f"Cannot generate proposal for quote in status {quote.status}")

            prompt = quote.request
            if additional_info and additional_info.strip():
                prompt = f"{quote.request}\nInformación adicional: {additional_info.strip()}"

        proposal = self._ai_service.generate_quote_proposal(prompt)

        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            if quote.status not in valid_statuses:
                raise ConflictError(f"Cannot generate proposal for quote in status {quote.status}")

            quote.request = prompt

            if proposal.needs_information or proposal.missing_info:
                quote.description = None
                quote.line_items = []
                quote.total = None
                quote.assumptions = []
                quote.mark_needs_information(proposal.missing_info or [])
                quote = self._uow.quotes.save(quote)
                self._uow.commit()
                return quote

            line_items = [
                QuoteLineItem(
                    id=None,
                    type=item.type,
                    description=item.description,
                    unit=item.unit,
                    quantity=item.quantity,
                    unit_price=Money(item.unit_price),
                )
                for item in proposal.line_items
            ]
            quote.description = proposal.description
            quote.line_items = line_items
            quote.assumptions = list(proposal.assumptions or [])
            quote.recalculate_total()
            quote.submit_for_review()
            quote = self._uow.quotes.save(quote)
            self._uow.commit()
            return quote


class ApproveQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId, principal: AccessPrincipal | None = None) -> Order:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            _authorize_quote_access(quote, principal)

            if quote.status == QUOTE_STATUS_PENDING_REVIEW:
                quote.approve()
                quote = self._uow.quotes.save(quote)
            elif quote.status != QUOTE_STATUS_APPROVED:
                raise ConflictError(f"Quote must be pending_review or approved to create an order, current: {quote.status}")

            existing = self._uow.orders.get_by_quote_id(quote_id)
            if existing is not None:
                self._uow.commit()
                return existing

            total = quote.total
            if total is None:
                raise ValidationDomainError("Quote total is missing")
            deposit = Money((total.amount * DEPOSIT_PERCENTAGE).quantize(total.amount))
            order = Order(
                id=None,
                quote_id=quote_id,
                carpenter_id=quote.carpenter_id,
                code=f"TC-{uuid.uuid4().hex}",
                total=total,
                deposit_amount=deposit,
                currency="USD",
                status=ORDER_STATUS_PENDING,
                created_at=None,
                updated_at=None,
            )
            order = self._uow.orders.save(order)
            self._uow.commit()
            return order


class RejectQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId, principal: AccessPrincipal | None = None) -> Quote:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            _authorize_quote_access(quote, principal)
            quote.reject()
            quote = self._uow.quotes.save(quote)
            self._uow.commit()
            return quote


