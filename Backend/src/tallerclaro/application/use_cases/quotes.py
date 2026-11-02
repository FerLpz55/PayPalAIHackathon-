"""Casos de uso para cotizaciones."""

from __future__ import annotations

import uuid

from tallerclaro.application.dtos import (
    CreateQuoteInput,
    CustomerInput,
    QuoteLineItemInput,
    QuoteProposalResult,
)
from tallerclaro.application.exceptions import ConflictError, NotFoundError, ValidationDomainError
from tallerclaro.application.ports import AIService, UnitOfWork
from tallerclaro.domain.entities import (
    DEPOSIT_PERCENTAGE,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_APPROVED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_PENDING_REVIEW,
    Customer,
    Money,
    Order,
    Quote,
    QuoteId,
    QuoteLineItem,
)


class CreateQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, input: CreateQuoteInput) -> Quote:
        with self._uow:
            carpenter = self._uow.carpenters.get_by_id(input.carpenter_id)
            if carpenter is None:
                raise NotFoundError("Carpenter", input.carpenter_id)
            customer_input = input.customer
            customer = Customer(
                id=None,
                name=customer_input.name,
                email=customer_input.email,
                phone=customer_input.phone,
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
            self._uow.commit()
            return quote


class GetQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId) -> Quote:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            return quote


class GenerateQuoteProposal:
    def __init__(self, uow: UnitOfWork, ai_service: AIService) -> None:
        self._uow = uow
        self._ai_service = ai_service

    def execute(self, quote_id: QuoteId) -> Quote:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            if quote.status not in {QUOTE_STATUS_DRAFT, QUOTE_STATUS_PENDING_REVIEW}:
                raise ConflictError(f"Cannot generate proposal for quote in status {quote.status}")

            proposal = self._ai_service.generate_quote_proposal(quote.request)

            if proposal.needs_information:
                quote.description = None
                quote.line_items = []
                quote.total = None
                quote.mark_needs_information("Missing information")
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
            quote.recalculate_total()
            quote.submit_for_review()
            quote = self._uow.quotes.save(quote)
            self._uow.commit()
            return quote


class ApproveQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId) -> Order:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)

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

    def execute(self, quote_id: QuoteId) -> Quote:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            quote.reject()
            quote = self._uow.quotes.save(quote)
            self._uow.commit()
            return quote
