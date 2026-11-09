"""Resultados de repositorios y mapeo SQL local. No ejecuta PostgreSQL."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from tallerclaro.domain.entities import Carpenter, Customer, Money, Order, Payment, Quote, QuoteLineItem
from tallerclaro.infrastructure.db.repositories import (
    PostgresCarpenterRepository, PostgresCustomerRepository, PostgresOrderRepository,
    PostgresPaymentRepository, PostgresQuoteRepository,
)
from tests.fakes import (
    FakeCarpenterRepository, FakeCustomerRepository, FakeOrderRepository,
    FakePaymentRepository, FakeQuoteRepository,
)

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


class ScriptedConnection:
    """Respuestas por llamada, sin interpretar SQL ni inventar un motor."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
    def execute(self, sql, params=()):
        self.calls.append((' '.join(sql.split()), params))
        assert self.responses, 'Unexpected SQL call'
        response = self.responses.pop(0)
        cursor = MagicMock()
        cursor.fetchone.return_value = response
        cursor.fetchall.return_value = response
        return cursor


REPOSITORIES = [
    (FakeCustomerRepository, PostgresCustomerRepository),
    (FakeCarpenterRepository, PostgresCarpenterRepository),
    (FakeQuoteRepository, PostgresQuoteRepository),
    (FakeOrderRepository, PostgresOrderRepository),
    (FakePaymentRepository, PostgresPaymentRepository),
]


@pytest.mark.parametrize('fake,postgres', REPOSITORIES)
def test_absent_entity_returns_none(fake, postgres):
    assert fake().get_by_id(999) is None
    conn = ScriptedConnection(None)
    assert postgres(conn).get_by_id(999) is None
    assert conn.calls[0][1] == (999,)
    assert 'WHERE' in conn.calls[0][0] and '%s' in conn.calls[0][0]
    assert conn.responses == []


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_customer_save_and_read_preserve_fields(kind):
    conn = ScriptedConnection((7, NOW, NOW), (7, 'Ana', 'ana@example.org', '123', NOW, NOW))
    repo = FakeCustomerRepository() if kind == 'fake' else PostgresCustomerRepository(conn)
    saved = repo.save(Customer(None, 'Ana', 'ana@example.org', '123'))
    read = repo.get_by_id(saved.id)
    assert read.id == saved.id
    assert (read.name, read.email, read.phone) == ('Ana', 'ana@example.org', '123')
    assert read.created_at is not None and read.updated_at is not None
    if kind == 'postgres':
        assert conn.calls[0][1] == ('Ana', 'ana@example.org', '123')
        assert conn.calls[1][1] == (7,)
        assert conn.responses == []


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_workshop_read_preserves_fields(kind):
    conn = ScriptedConnection((7, 'Ana', 'Taller', 'ana@example.org', None, NOW))
    if kind == 'fake':
        repo = FakeCarpenterRepository()
        repo.seed(Carpenter(7, 'Ana', 'Taller', 'ana@example.org', None, NOW))
    else:
        repo = PostgresCarpenterRepository(conn)
    read = repo.get_by_id(7)
    assert (read.id, read.name, read.workshop_name, read.email, read.phone) == (7, 'Ana', 'Taller', 'ana@example.org', None)
    if kind == 'postgres':
        assert conn.calls[0][1] == (7,)


def quote_row(quote):
    return (quote.id, quote.customer_id, quote.carpenter_id, quote.request, quote.description,
            quote.total.amount if quote.total else None, quote.status, quote.currency,
            NOW, NOW, quote.assumptions, quote.missing_info)


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_quote_preserves_items_and_clarification_fields(kind):
    quote = Quote(None, 1, 2, 'Mesa', 'Roble', [QuoteLineItem(None, 'material', 'Roble', 'u', Decimal('2'), Money('10'))], Money('20'), 'pending_review', assumptions=['Barniz'])
    conn = ScriptedConnection((7, NOW, NOW), [], (11,))
    repo = FakeQuoteRepository() if kind == 'fake' else PostgresQuoteRepository(conn)
    saved = repo.save(quote)
    assert saved.id is not None
    assert saved.line_items[0].id is not None
    if kind == 'postgres':
        conn.responses.extend([quote_row(saved), [(11, 'material', 'Roble', 'u', Decimal('2'), Decimal('10'))]])
    read = repo.get_by_id(saved.id)
    assert read.assumptions == ['Barniz'] and read.missing_info == []
    assert read.line_items[0].amount == Money('20')
    assert read.total == Money('20')
    read.line_items = []
    read.description = None
    read.total = None
    read.mark_needs_information(['Medidas'])
    if kind == 'postgres':
        conn.responses.extend([(7, NOW, NOW), [(11,)], None])
    repo.save(read)
    if kind == 'postgres':
        conn.responses.extend([quote_row(read), []])
    clarified = repo.get_by_id(saved.id)
    assert clarified.line_items == [] and clarified.total is None
    assert clarified.missing_info == ['Medidas'] and clarified.assumptions == []
    if kind == 'postgres':
        assert conn.calls[0][1][-2:] == (['Barniz'], [])
        assert any('SET activo = false' in sql and params == (11, 7) for sql, params in conn.calls)
        assert all('DELETE' not in sql for sql, _ in conn.calls)
        assert conn.responses == []


def order_entity(code, workshop, created=None):
    return Order(None, {'TC-1': 5, 'TC-2': 6, 'TC-3': 7}[code], workshop, code, Money('200'), Money('100'), 'USD', 'pending', created, created, date(2026, 12, 1))


def order_row(order):
    return (order.id, order.quote_id, order.carpenter_id, order.code, order.total.amount,
            order.deposit_amount.amount, order.currency, order.status, order.created_at or NOW,
            order.updated_at or NOW, order.estimated_delivery_date)


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_order_save_lookup_workshop_filter_and_pagination(kind):
    order = order_entity('TC-1', 2)
    conn = ScriptedConnection((7, NOW, NOW))
    repo = FakeOrderRepository() if kind == 'fake' else PostgresOrderRepository(conn)
    saved = repo.save(order)
    if kind == 'fake':
        repo.save(order_entity('TC-2', 3))
        repo.save(order_entity('TC-3', 2))
    else:
        conn.responses.extend([order_row(saved), order_row(saved), [order_row(saved)], (2,)])
    read = repo.get_by_id(saved.id)
    assert (read.total, read.deposit_amount, read.currency, read.estimated_delivery_date) == (Money('200'), Money('100'), 'USD', date(2026, 12, 1))
    assert repo.get_by_quote_id(5).id == saved.id
    page = repo.list_by_carpenter(2, 1, 1)
    assert len(page) == 1 and page[0].carpenter_id == 2 and page[0].id == saved.id
    assert repo.count_by_carpenter(2) == 2
    if kind == 'postgres':
        sql, params = conn.calls[-2]
        assert params == (2, 1, 1)
        assert 'WHERE id_carpintero = %s' in sql
        assert 'ORDER BY fecha_creacion DESC' in sql
        assert 'LIMIT %s OFFSET %s' in sql
        assert conn.responses == []


def payment_row(payment):
    return (payment.id, payment.order_id, payment.type, payment.amount.amount, payment.currency,
            payment.status, payment.paypal_order_id, payment.paypal_capture_id,
            payment.created_at or NOW, payment.updated_at or NOW, payment.paid_at,
            payment.idempotency_key, payment.request_fingerprint, payment.approval_url)


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_payment_save_read_and_order_listing(kind):
    payment = Payment(None, 7, 'deposit', Money('100'), 'USD', 'completed', 'PP-1', 'CAP-1', None, None, NOW)
    conn = ScriptedConnection((9, NOW, NOW))
    repo = FakePaymentRepository() if kind == 'fake' else PostgresPaymentRepository(conn)
    saved = repo.save(payment)
    if kind == 'fake':
        repo.save(Payment(None, 8, 'balance', Money('50'), 'USD', 'pending', 'PP-2', None, None, None, None))
    else:
        conn.responses.extend([payment_row(saved), [payment_row(saved)]])
    read = repo.get_by_id(saved.id)
    assert (read.amount, read.currency, read.paypal_order_id, read.paypal_capture_id, read.paid_at) == (Money('100'), 'USD', 'PP-1', 'CAP-1', NOW)
    assert [p.id for p in repo.list_by_order(7)] == [saved.id]
    if kind == 'postgres':
        assert conn.calls[0][1] == (7, 'deposit', Decimal('100'), 'USD', 'completed', 'PP-1', 'CAP-1', NOW, None, None, None)
        assert conn.calls[-1][1] == (7,)
        assert 'WHERE id_pedido = %s' in conn.calls[-1][0]
        assert conn.responses == []


@pytest.mark.parametrize('kind', ['fake', 'postgres'])
def test_payment_lookup_by_paypal_order_and_stale_pending(kind):
    stale_at = NOW - timedelta(minutes=10)
    payment = Payment(None, 7, 'deposit', Money('100'), 'USD', 'pending',
                      'PP-1', None, None, stale_at, None)
    if kind == 'fake':
        repo = FakePaymentRepository()
        saved = repo.save(payment)
        saved.updated_at = stale_at
        found = repo.get_by_paypal_order_id('PP-1')
        assert found is not None and found.paypal_order_id == 'PP-1'
        assert repo.get_by_paypal_order_id('PP-UNKNOWN') is None
        assert [p.id for p in repo.list_stale_pending(NOW, 10)] == [saved.id]
        assert repo.list_stale_pending(NOW - timedelta(minutes=30), 10) == []
        return

    row = payment_row(payment)
    lookup_conn = ScriptedConnection(row, None)
    lookup_repo = PostgresPaymentRepository(lookup_conn)
    found = lookup_repo.get_by_paypal_order_id('PP-1')
    assert found is not None and found.paypal_order_id == 'PP-1'
    assert lookup_repo.get_by_paypal_order_id('PP-UNKNOWN') is None
    assert 'WHERE paypal_order_id = %s' in lookup_conn.calls[0][0]
    assert lookup_conn.calls[0][1] == ('PP-1',)
    assert lookup_conn.responses == []

    stale_conn = ScriptedConnection([row], [])
    stale_repo = PostgresPaymentRepository(stale_conn)
    listed = stale_repo.list_stale_pending(NOW, 10)
    stale_repo.list_stale_pending(NOW - timedelta(minutes=30), 10)
    assert [p.id for p in listed] == [payment.id]
    assert "estado = 'pending'" in stale_conn.calls[0][0]
    assert stale_conn.calls[0][1] == (NOW, 10)
    assert stale_conn.responses == []
