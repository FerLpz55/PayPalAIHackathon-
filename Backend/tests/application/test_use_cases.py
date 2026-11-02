"""Pruebas de casos de uso."""

from decimal import Decimal

import pytest

from tallerclaro.application.dtos import CreateQuoteInput, CustomerInput, UpdateOrderInput
from tallerclaro.application.exceptions import ConflictError, NotFoundError
from tallerclaro.application.use_cases import (
    ApproveQuote,
    CapturePayment,
    CreateOrderPayment,
    CreateQuote,
    GenerateQuoteProposal,
    GetOrder,
    ListOrders,
    RejectQuote,
    UpdateOrder,
)
from tallerclaro.domain.entities import (
    ORDER_STATUS_DELIVERED,
    ORDER_STATUS_IN_PROGRESS,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PENDING,
    QUOTE_STATUS_PENDING_REVIEW,
    Carpenter,
    CarpenterId,
    CustomerId,
    Money,
    Order,
    OrderId,
    Payment,
    QuoteId,
)
from tallerclaro.domain.value_objects import Money as MoneyVO
from tests.fakes import FakeAIService, FakePaymentProcessor, FakeUnitOfWork


def test_create_quote():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    use_case = CreateQuote(uow)
    quote = use_case.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa de centro",
        )
    )
    assert quote.id is not None
    assert quote.status == "draft"


def test_generate_quote_proposal():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    create = CreateQuote(uow)
    quote = create.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    ai = FakeAIService()
    use_case = GenerateQuoteProposal(uow, ai)
    result = use_case.execute(quote.id)
    assert result.status == QUOTE_STATUS_PENDING_REVIEW
    assert result.total.amount == Decimal("200.00")


def test_approve_quote_creates_order_idempotently():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    create = CreateQuote(uow)
    quote = create.execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    use_case = ApproveQuote(uow)
    order1 = use_case.execute(quote.id)
    order2 = use_case.execute(quote.id)
    assert order1.id == order2.id
    assert order1.deposit_amount.amount == Decimal("100.00")


def test_reject_quote_not_pending_review_fails():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    with pytest.raises(ConflictError):
        RejectQuote(uow).execute(quote.id)


def test_create_payment_and_capture():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)

    processor = FakePaymentProcessor(success=True)
    deposit_intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    assert deposit_intent.amount == Decimal("100.00")

    CapturePayment(uow, processor).execute(deposit_intent.payment_id)
    updated = GetOrder(uow).execute(order.id)
    assert updated.status == ORDER_STATUS_PENDING

    balance_intent = CreateOrderPayment(uow, processor).execute(order.id, "balance")
    assert balance_intent.amount == Decimal("100.00")
    CapturePayment(uow, processor).execute(balance_intent.payment_id)

    updated = GetOrder(uow).execute(order.id)
    assert updated.status == ORDER_STATUS_PAID


def test_capture_duplicate_returns_existing():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)
    processor = FakePaymentProcessor(success=True)
    intent = CreateOrderPayment(uow, processor).execute(order.id, "deposit")
    CapturePayment(uow, processor).execute(intent.payment_id)
    captured2 = CapturePayment(uow, processor).execute(intent.payment_id)
    assert captured2.status == "completed"


def test_cannot_deliver_unpaid_order():
    uow = FakeUnitOfWork()
    uow.carpenters.seed(Carpenter(id=CarpenterId(1), name="José", workshop_name="Taller", email="j@example.com", phone=None))
    quote = CreateQuote(uow).execute(
        CreateQuoteInput(
            customer=CustomerInput(name="Carlos", email="carlos@example.com", phone=None),
            carpenter_id=1,
            request="Mesa",
        )
    )
    GenerateQuoteProposal(uow, FakeAIService()).execute(quote.id)
    order = ApproveQuote(uow).execute(quote.id)
    uow.orders.save(Order(
        id=order.id,
        quote_id=order.quote_id,
        carpenter_id=order.carpenter_id,
        code=order.code,
        total=order.total,
        deposit_amount=order.deposit_amount,
        currency=order.currency,
        status=ORDER_STATUS_IN_PROGRESS,
        created_at=order.created_at,
        updated_at=order.updated_at,
    ))
    with pytest.raises(ConflictError):
        UpdateOrder(uow).execute(order.id, UpdateOrderInput(status=ORDER_STATUS_DELIVERED))
