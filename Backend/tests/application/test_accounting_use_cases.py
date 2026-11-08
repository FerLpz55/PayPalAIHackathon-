"""Pruebas de los casos de uso del asistente contable."""

from datetime import datetime, timezone

import pytest

from tallerclaro.application.exceptions import DomainError, ValidationDomainError
from tallerclaro.application.use_cases import AskAccountingAssistant, GetWorkshopFinancialSummary
from tallerclaro.domain.entities import (
    CarpenterId,
    Money,
    Order,
    OrderId,
    Payment,
    QuoteId,
)
from tests.fakes import FakeAccountingAssistant, FakeUnitOfWork


def _seed_order(uow: FakeUnitOfWork, quote_id: int, total: str, carpenter_id: int = 1) -> Order:
    total_money = Money(total)
    with uow:
        order = uow.orders.save(
            Order(
                id=None,
                quote_id=QuoteId(quote_id),
                carpenter_id=CarpenterId(carpenter_id),
                code=f"TC-{quote_id}",
                total=total_money,
                deposit_amount=Money(total_money.amount / 2),
                currency="USD",
                status="in_progress",
                created_at=None,
                updated_at=None,
            )
        )
        uow.commit()
    return order


def _seed_completed_payment(uow: FakeUnitOfWork, order_id: OrderId, amount: str) -> None:
    with uow:
        uow.payments.save(
            Payment(
                id=None,
                order_id=order_id,
                type="deposit",
                amount=Money(amount),
                currency="USD",
                status="completed",
                paypal_order_id=f"P-{order_id}",
                paypal_capture_id=f"C-{order_id}",
                created_at=None,
                updated_at=None,
                paid_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()


def test_summary_only_includes_the_workshop_orders():
    uow = FakeUnitOfWork()
    mine = _seed_order(uow, 1, "1200")
    _seed_completed_payment(uow, mine.id, "600")
    _seed_order(uow, 2, "999", carpenter_id=2)

    summary = GetWorkshopFinancialSummary(uow).execute(CarpenterId(1))

    assert summary.orders_count == 1
    assert summary.total_contracted == Money("1200")
    assert summary.collected_total == Money("600")


def test_summary_reads_every_page_of_orders():
    uow = FakeUnitOfWork()
    for index in range(1, 151):
        _seed_order(uow, index, "10")

    summary = GetWorkshopFinancialSummary(uow).execute(CarpenterId(1))

    assert summary.orders_count == 150
    assert summary.total_contracted == Money("1500")


def test_assistant_is_called_outside_the_transaction_with_aggregates_only():
    uow = FakeUnitOfWork()
    order = _seed_order(uow, 1, "1200")
    _seed_completed_payment(uow, order.id, "600")
    assistant = FakeAccountingAssistant(uow, answer="  You collected 600 USD.  ")

    result = AskAccountingAssistant(uow, assistant).execute(CarpenterId(1), "  How much did I collect?  ")

    assert result.answer == "You collected 600 USD."
    assert result.question == "How much did I collect?"
    assert assistant.open_transactions_at_call == [0]
    summary, question = assistant.calls[0]
    assert question == "How much did I collect?"
    assert summary.collected_total == Money("600")


@pytest.mark.parametrize("question", ["", "  ", "hi", "x" * 501])
def test_assistant_rejects_invalid_questions(question):
    uow = FakeUnitOfWork()
    assistant = FakeAccountingAssistant(uow)
    with pytest.raises(ValidationDomainError):
        AskAccountingAssistant(uow, assistant).execute(CarpenterId(1), question)
    assert assistant.calls == []


def test_assistant_empty_answer_is_rejected():
    uow = FakeUnitOfWork()
    assistant = FakeAccountingAssistant(uow, answer="   ")
    with pytest.raises(DomainError) as exc:
        AskAccountingAssistant(uow, assistant).execute(CarpenterId(1), "How am I doing?")
    assert exc.value.code == "AI_RESPONSE_INVALID"


def test_assistant_answer_is_truncated():
    uow = FakeUnitOfWork()
    assistant = FakeAccountingAssistant(uow, answer="a" * 2000)
    result = AskAccountingAssistant(uow, assistant).execute(CarpenterId(1), "How am I doing?")
    assert len(result.answer) == 1500

