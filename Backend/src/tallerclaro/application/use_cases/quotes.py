"""Casos de uso para cotizaciones."""

from __future__ import annotations

import logging
import uuid

from tallerclaro.application.dtos import (
    AccessPrincipal,
    CreatedQuoteResult,
    CreateQuoteInput,
    CustomerContext,
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
from tallerclaro.application.interfaces import AIService, UnitOfWork
from tallerclaro.application.use_cases.authorization import authorize_workshop_or_customer
from tallerclaro.domain.entities import (
    DEPOSIT_PERCENTAGE,
    ORDER_STATUS_PENDING,
    QUOTE_EDITABLE_STATUSES,
    QUOTE_STATUS_APPROVED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_NEEDS_INFORMATION,
    QUOTE_STATUS_PENDING_REVIEW,
    QUOTE_STATUSES,
    CarpenterId,
    Customer,
    CustomerId,
    Money,
    Order,
    Quote,
    QuoteId,
    QuoteLineItem,
)


_logger = logging.getLogger(__name__)


def _authorize_quote_access(quote: Quote, principal: AccessPrincipal | None) -> None:
    authorize_workshop_or_customer(
        principal,
        carpenter_id=quote.carpenter_id,
        quote_id=quote.id,
        resource_name="quote",
    )


class VerifyCustomerToken:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, token: str) -> AccessPrincipal | None:
        with self._uow:
            result = self._uow.tokens.verify(token)
        if result is None:
            return None
        customer_id, quote_id = result
        return AccessPrincipal(
            kind="customer",
            customer_id=customer_id,
            quote_id=quote_id,
        )


class CreateQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, input: CreateQuoteInput) -> CreatedQuoteResult:
        with self._uow:
            carpenter = self._uow.carpenters.get_by_id(input.carpenter_id)
            if carpenter is None:
                raise NotFoundError("Carpenter", input.carpenter_id)

            customer = self._uow.customers.save(self._build_normalized_customer(input.customer))
            quote = self._uow.quotes.save(self._build_draft_quote(customer.id, input))
            customer_token = self._uow.tokens.create(customer.id, quote.id)
            self._uow.commit()
            return CreatedQuoteResult(quote=quote, customer_token=customer_token)

    @staticmethod
    def _build_normalized_customer(customer_input: CustomerInput) -> Customer:
        normalized_phone = (
            (customer_input.phone.strip() or None) if customer_input.phone else None
        )
        return Customer(
            id=None,
            name=customer_input.name.strip(),
            email=customer_input.email.strip().lower(),
            phone=normalized_phone,
        )

    @staticmethod
    def _build_draft_quote(customer_id: CustomerId, input: CreateQuoteInput) -> Quote:
        return Quote(
            id=None,
            customer_id=customer_id,
            carpenter_id=input.carpenter_id,
            request=input.request,
            description=None,
            line_items=[],
            total=None,
            status=QUOTE_STATUS_DRAFT,
        )


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


class ListQuotes:
    """Lista las solicitudes/cotizaciones de un taller con el nombre del cliente."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(
        self,
        carpenter_id: CarpenterId,
        statuses: tuple[str, ...] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[Quote, str | None, str | None]], int]:
        if statuses:
            unknown = sorted(set(statuses) - QUOTE_STATUSES)
            if unknown:
                raise ValidationDomainError(f"Unknown quote status: {', '.join(unknown)}")
        with self._uow:
            quotes = self._uow.quotes.list_by_carpenter(carpenter_id, statuses, limit, offset)
            total = self._uow.quotes.count_by_carpenter(carpenter_id, statuses)
            enriched: list[tuple[Quote, str | None, str | None]] = []
            for quote in quotes:
                customer = self._uow.customers.get_by_id(quote.customer_id)
                enriched.append(
                    (quote, customer.name if customer else None, customer.email if customer else None)
                )
            return enriched, total


class GenerateQuoteProposal:
    """Genera una propuesta de cotización con IA en 3 fases sin red dentro de SQL."""

    def __init__(self, uow: UnitOfWork, ai_service: AIService) -> None:
        self._uow = uow
        self._ai_service = ai_service

    def execute(
        self,
        quote_id: QuoteId,
        additional_info: str | None = None,
        principal: AccessPrincipal | None = None,
    ) -> Quote:
        # Fase 1: Cargar cotización, autorizar y construir el prompt dentro del UoW.
        prompt, original_request, original_updated_at = self._prepare_ai_prompt(
            quote_id, additional_info, principal
        )

        # Fase 2: Consultar el servicio de IA fuera de la transacción SQL.
        proposal = self._ai_service.generate_quote_proposal(prompt)

        # Fase 3: Revalidar que la cotización no cambió y persistir el resultado.
        return self._apply_proposal_and_save(
            quote_id=quote_id,
            prompt=prompt,
            original_request=original_request,
            original_updated_at=original_updated_at,
            proposal=proposal,
            principal=principal,
        )

    def _prepare_ai_prompt(
        self,
        quote_id: QuoteId,
        additional_info: str | None,
        principal: AccessPrincipal | None,
    ) -> tuple[str, str, object]:
        with self._uow:
            quote = self._load_editable_quote(quote_id, principal)
            prompt = quote.request
            if additional_info and additional_info.strip():
                prompt = f"{quote.request}\nInformación adicional: {additional_info.strip()}"
            return prompt, quote.request, quote.updated_at

    def _apply_proposal_and_save(
        self,
        *,
        quote_id: QuoteId,
        prompt: str,
        original_request: str,
        original_updated_at: object,
        proposal: QuoteProposalResult,
        principal: AccessPrincipal | None,
    ) -> Quote:
        with self._uow:
            quote = self._load_editable_quote(
                quote_id,
                principal,
                expected_request=original_request,
                expected_updated_at=original_updated_at,
            )
            quote.request = prompt

            if proposal.needs_information or proposal.missing_info:
                return self._save_missing_info_proposal(quote, proposal)
            return self._save_priced_proposal(quote, proposal)

    def _load_editable_quote(
        self,
        quote_id: QuoteId,
        principal: AccessPrincipal | None,
        *,
        expected_request: str | None = None,
        expected_updated_at: object = None,
    ) -> Quote:
        quote = self._uow.quotes.get_by_id(quote_id)
        if quote is None:
            raise NotFoundError("Quote", quote_id)
        _authorize_quote_access(quote, principal)
        if expected_request is not None and (
            quote.request != expected_request or quote.updated_at != expected_updated_at
        ):
            raise ConflictError("Quote changed while generating proposal")
        if quote.status not in QUOTE_EDITABLE_STATUSES:
            raise ConflictError(f"Cannot generate proposal for quote in status {quote.status}")
        return quote

    def _save_missing_info_proposal(self, quote: Quote, proposal: QuoteProposalResult) -> Quote:
        quote.description = None
        quote.line_items = []
        quote.total = None
        quote.assumptions = []
        quote.mark_needs_information(proposal.missing_info or [])
        quote = self._uow.quotes.save(quote)
        self._uow.commit()
        return quote

    def _save_priced_proposal(self, quote: Quote, proposal: QuoteProposalResult) -> Quote:
        quote.description = proposal.description
        quote.line_items = self._to_domain_line_items(proposal.line_items)
        quote.assumptions = list(proposal.assumptions or [])
        quote.recalculate_total()
        quote.submit_for_review()
        quote = self._uow.quotes.save(quote)
        self._uow.commit()
        return quote

    @staticmethod
    def _to_domain_line_items(items: list[QuoteLineItemInput]) -> list[QuoteLineItem]:
        return [
            QuoteLineItem(
                id=None,
                type=item.type,
                description=item.description,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=Money(item.unit_price),
            )
            for item in items
        ]


class GetCustomerContext:
    """Recupera cotización, pedido e intentos de pago del cliente autenticado."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, principal: AccessPrincipal) -> CustomerContext:
        if not principal.is_customer or principal.quote_id is None:
            raise ForbiddenError("A customer token is required")
        with self._uow:
            quote = self._uow.quotes.get_by_id(principal.quote_id)
            if quote is None:
                raise NotFoundError("Quote", principal.quote_id)
            if (
                principal.customer_id is not None
                and quote.customer_id != principal.customer_id
            ):
                raise ForbiddenError("Not authorized to access this quote")

            order = self._uow.orders.get_by_quote_id(quote.id)
            payments = (
                self._uow.payments.list_by_order(order.id) if order is not None else []
            )
            return CustomerContext(quote=quote, order=order, payments=payments)


class ReissueCustomerAccess:
    """Emite un token nuevo para el cliente; solo el taller autenticado puede hacerlo."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId, principal: AccessPrincipal | None) -> str:
        if principal is None or not principal.is_workshop:
            raise ForbiddenError("Only the authenticated workshop can reissue access")
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            _authorize_quote_access(quote, principal)
            customer = self._uow.customers.get_by_id(quote.customer_id)
            if customer is None:
                raise NotFoundError("Customer", quote.customer_id)

            revoked = self._uow.tokens.revoke_for_quote(quote.id)
            token = self._uow.tokens.create(quote.customer_id, quote.id)
            self._uow.commit()

        _logger.info(
            "customer_access_reissued",
            extra={
                "quote_id": int(quote.id),
                "customer_id": int(quote.customer_id),
                "revoked_tokens": revoked,
            },
        )
        return token


class ApproveQuote:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, quote_id: QuoteId, principal: AccessPrincipal | None = None) -> Order:
        with self._uow:
            quote = self._uow.quotes.get_by_id(quote_id)
            if quote is None:
                raise NotFoundError("Quote", quote_id)
            _authorize_quote_access(quote, principal)

            quote = self._approve_if_pending_review(quote)

            existing_order = self._uow.orders.get_by_quote_id(quote_id)
            if existing_order is not None:
                self._uow.commit()
                return existing_order

            order = self._uow.orders.save(self._build_pending_order(quote))
            self._uow.commit()
            return order

    def _approve_if_pending_review(self, quote: Quote) -> Quote:
        if quote.status == QUOTE_STATUS_PENDING_REVIEW:
            quote.approve()
            return self._uow.quotes.save(quote)
        if quote.status != QUOTE_STATUS_APPROVED:
            raise ConflictError(
                f"Quote must be pending_review or approved to create an order, current: {quote.status}"
            )
        return quote

    @staticmethod
    def _build_pending_order(quote: Quote) -> Order:
        total = quote.total
        deposit = quote.deposit_amount
        if total is None or deposit is None:
            raise ValidationDomainError("Quote total is missing")
        return Order(
            id=None,
            quote_id=quote.id,
            carpenter_id=quote.carpenter_id,
            code=Order.code_for_quote(quote.id),
            total=total,
            deposit_amount=deposit,
            currency="USD",
            status=ORDER_STATUS_PENDING,
            created_at=None,
            updated_at=None,
        )


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
