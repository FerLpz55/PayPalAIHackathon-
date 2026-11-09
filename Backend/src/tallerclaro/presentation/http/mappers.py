"""Mapeadores puros de entidades y DTOs de dominio hacia esquemas HTTP."""

from __future__ import annotations

from tallerclaro.application.dtos import (
    CustomerContext,
    MarketPriceReference,
    OrderDetailResult,
)
from tallerclaro.domain.accounting import WorkshopFinancialSummary
from tallerclaro.domain.entities import Order, Payment, Quote, QuoteLineItem
from tallerclaro.presentation.http.schemas.accounting import FinancialSummaryResponse
from tallerclaro.presentation.http.schemas.customer import CustomerContextResponse
from tallerclaro.presentation.http.schemas.orders import (
    OrderDetailResponse,
    OrderResponse,
    PaymentSummary,
)
from tallerclaro.presentation.http.schemas.payments import PaymentResponse
from tallerclaro.presentation.http.schemas.quotes import (
    QuoteLineItemResponse,
    QuoteResponse,
    SuggestedProductResponse,
)


def to_suggested_product_response(ref: MarketPriceReference) -> SuggestedProductResponse:
    return SuggestedProductResponse(
        title=ref.title,
        price_usd=float(ref.price_usd),
        source=ref.source,
        url=ref.url,
        image_url=ref.image_url,
    )


def to_line_item_response(item: QuoteLineItem) -> QuoteLineItemResponse:
    return QuoteLineItemResponse(
        id=str(item.id) if item.id is not None else "",
        type=item.type,
        description=item.description,
        unit=item.unit,
        quantity=float(item.quantity),
        unit_amount=float(item.unit_price.amount),
        amount=float(item.amount.amount),
    )


def to_quote_response(
    quote: Quote,
    include_missing: bool = False,
    customer_token: str | None = None,
    suggested_products: list[MarketPriceReference] | None = None,
) -> QuoteResponse:
    deposit = float(quote.deposit_amount.amount) if quote.deposit_amount is not None else None
    balance = float(quote.balance_amount.amount) if quote.balance_amount is not None else None
    missing_info = (
        list(quote.missing_info)
        if quote.missing_info is not None
        else ([] if include_missing else None)
    )
    products = [
        to_suggested_product_response(p)
        for p in (suggested_products or [])
    ]
    return QuoteResponse(
        id=str(quote.id) if quote.id is not None else "",
        customer_id=str(quote.customer_id),
        carpenter_id=str(quote.carpenter_id),
        request=quote.request,
        description=quote.description,
        items=[to_line_item_response(item) for item in quote.line_items],
        currency=quote.currency,
        total=float(quote.total.amount) if quote.total is not None else None,
        deposit_amount=deposit,
        balance_amount=balance,
        status=quote.status,
        customer_token=customer_token,
        assumptions=list(quote.assumptions) if quote.assumptions else None,
        missing_info=missing_info,
        suggested_products=products,
        created_at=quote.created_at.isoformat() if quote.created_at else None,
        updated_at=quote.updated_at.isoformat() if quote.updated_at else None,
    )


def to_order_response(
    order: Order,
    customer_name: str | None = None,
    customer_email: str | None = None,
    project_request: str | None = None,
) -> OrderResponse:
    return OrderResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.balance_amount.amount),
        currency=order.currency,
        status=order.status,
        estimated_delivery_date=order.estimated_delivery_date,
        customer_name=customer_name,
        customer_email=customer_email,
        project_request=project_request,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
    )


def to_order_detail_response(detail: OrderDetailResult) -> OrderDetailResponse:
    order = detail.order
    return OrderDetailResponse(
        id=str(order.id),
        quote_id=str(order.quote_id),
        code=order.code,
        total=float(order.total.amount),
        deposit_amount=float(order.deposit_amount.amount),
        balance_amount=float(order.balance_amount.amount),
        currency=order.currency,
        status=order.status,
        estimated_delivery_date=order.estimated_delivery_date,
        created_at=order.created_at.isoformat() if order.created_at else None,
        updated_at=order.updated_at.isoformat() if order.updated_at else None,
        payments=[
            PaymentSummary(
                id=str(payment.id),
                type=payment.type,
                amount=float(payment.amount.amount),
                status=payment.status,
                paypal_order_id=payment.paypal_order_id,
            )
            for payment in detail.payments
        ],
        paid_amount=float(detail.paid_amount.amount),
        remaining_balance=float(detail.remaining_balance.amount),
        customer_name=detail.customer_name,
        customer_email=detail.customer_email,
        project_request=detail.project_request,
    )


def to_customer_context_response(context: CustomerContext) -> CustomerContextResponse:
    """Expone los recursos del cliente autenticado con los campos existentes."""
    return CustomerContextResponse(
        quote=to_quote_response(context.quote, include_missing=True),
        order=to_order_response(context.order) if context.order is not None else None,
        payments=[to_payment_response(payment) for payment in context.payments],
    )


def to_payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=str(payment.id),
        order_id=str(payment.order_id),
        type=payment.type,
        amount=float(payment.amount.amount),
        currency=payment.currency,
        status=payment.status,
        paypal_order_id=payment.paypal_order_id,
        paypal_capture_id=payment.paypal_capture_id,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
        paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
    )


def to_financial_summary_response(
    summary: WorkshopFinancialSummary,
) -> FinancialSummaryResponse:
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

