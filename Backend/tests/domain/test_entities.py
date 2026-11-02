"""Pruebas de entidades de dominio."""

from decimal import Decimal

import pytest

from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_APPROVED,
    QUOTE_STATUS_DRAFT,
    QUOTE_STATUS_PENDING_REVIEW,
    QUOTE_STATUS_REJECTED,
    Customer,
    Money,
    Order,
    Quote,
    QuoteLineItem,
)
from tallerclaro.domain.exceptions import ConflictError, ValidationDomainError
from tallerclaro.domain.value_objects import Money as MoneyVO


def test_money_rounding():
    m = MoneyVO(Decimal("10.005"))
    assert m.amount == Decimal("10.01")


def test_quote_recalculate_total():
    quote = Quote(
        id=None,
        customer_id=1,
        carpenter_id=1,
        request="mesa",
        description=None,
        line_items=[
            QuoteLineItem(
                id=None,
                type="material",
                description="Madera",
                unit="piece",
                quantity=Decimal("2"),
                unit_price=MoneyVO(Decimal("100.00")),
            ),
            QuoteLineItem(
                id=None,
                type="labor",
                description="Carpintería",
                unit="service",
                quantity=Decimal("1"),
                unit_price=MoneyVO(Decimal("150.00")),
            ),
        ],
        total=None,
        status=QUOTE_STATUS_DRAFT,
    )
    quote.recalculate_total()
    assert quote.total.amount == Decimal("350.00")


def test_quote_submit_for_review_requires_positive_total():
    quote = Quote(
        id=None,
        customer_id=1,
        carpenter_id=1,
        request="mesa",
        description=None,
        line_items=[],
        total=None,
        status=QUOTE_STATUS_DRAFT,
    )
    with pytest.raises(ValidationDomainError):
        quote.submit_for_review()


def test_quote_approve_requires_pending_review():
    quote = Quote(
        id=None,
        customer_id=1,
        carpenter_id=1,
        request="mesa",
        description="Mesa de prueba",
        line_items=[
            QuoteLineItem(
                id=None,
                type="material",
                description="Madera",
                unit="piece",
                quantity=Decimal("1"),
                unit_price=MoneyVO(Decimal("100.00")),
            )
        ],
        total=MoneyVO(Decimal("100.00")),
        status=QUOTE_STATUS_DRAFT,
    )
    with pytest.raises(ConflictError):
        quote.approve()


def test_order_valid_transitions():
    order = Order(
        id=None,
        quote_id=1,
        carpenter_id=1,
        code="TC-1",
        total=MoneyVO(Decimal("100.00")),
        deposit_amount=MoneyVO(Decimal("50.00")),
        currency="USD",
        status=ORDER_STATUS_PENDING,
        created_at=None,
        updated_at=None,
    )
    order.update_status(ORDER_STATUS_PAID)
    order.update_status(ORDER_STATUS_IN_PROGRESS)
    with pytest.raises(ConflictError):
        order.update_status(ORDER_STATUS_PENDING)


def test_order_deposit_cannot_exceed_total():
    with pytest.raises(ValidationDomainError):
        Order(
            id=None,
            quote_id=1,
            carpenter_id=1,
            code="TC-1",
            total=MoneyVO(Decimal("100.00")),
            deposit_amount=MoneyVO(Decimal("150.00")),
            currency="USD",
            status=ORDER_STATUS_PENDING,
            created_at=None,
            updated_at=None,
        )
