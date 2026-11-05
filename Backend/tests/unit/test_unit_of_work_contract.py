"""Contrato del Unit of Work: aislamiento, rollback y devolución de conexiones."""

from __future__ import annotations

import pytest

from tallerclaro.domain.entities import Customer
from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork
from tests.fakes import FakeUnitOfWork


class _Conn:
    def __init__(self, cid: int) -> None:
        self.cid = cid
        self.committed = 0
        self.rolled_back = 0

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class _Database:
    def __init__(self) -> None:
        self.borrowed: list[_Conn] = []
        self.returned: list[_Conn] = []
        self._next = 1

    def get_connection(self) -> _Conn:
        conn = _Conn(self._next)
        self._next += 1
        self.borrowed.append(conn)
        return conn

    def put_connection(self, conn: _Conn) -> None:
        self.returned.append(conn)


def _customer() -> Customer:
    return Customer(id=None, name="Ana", email="ana@example.com", phone=None)


def test_independent_fake_units_of_work_do_not_share_state():
    first = FakeUnitOfWork()
    second = FakeUnitOfWork()

    with first:
        first.customers.save(_customer())
        first.commit()

    with first:
        assert first.customers.get_by_id(1) is not None
    with second:
        assert second.customers.get_by_id(1) is None


def test_postgres_units_of_work_return_every_connection_even_on_error():
    database = _Database()

    with PostgresUnitOfWork(database) as uow:
        first_conn = uow.get_connection()
        with pytest.raises(RuntimeError):
            with PostgresUnitOfWork(database) as nested:
                nested.get_connection()
                raise RuntimeError("boom")
        uow.commit()

    assert len(database.borrowed) == 2
    assert len(database.returned) == 2
    assert first_conn.committed == 1
    assert database.borrowed[1].rolled_back == 1


def test_postgres_unit_of_work_rolls_back_without_commit():
    database = _Database()

    with PostgresUnitOfWork(database) as uow:
        conn = uow.get_connection()

    assert conn.rolled_back == 1
    assert conn.committed == 0
    assert database.returned == [conn]


def test_connection_is_returned_even_if_rollback_fails():
    class FailingRollbackConn(_Conn):
        def rollback(self) -> None:
            super().rollback()
            raise RuntimeError("rollback failed")

    class FailingDatabase(_Database):
        def get_connection(self) -> FailingRollbackConn:
            conn = FailingRollbackConn(self._next)
            self._next += 1
            self.borrowed.append(conn)
            return conn

    database = FailingDatabase()

    with pytest.raises(RuntimeError, match="rollback failed"):
        with PostgresUnitOfWork(database) as uow:
            uow.get_connection()

    assert len(database.returned) == 1


def test_unit_of_work_repositories_are_only_available_while_open():
    uow = PostgresUnitOfWork(_Database())

    with pytest.raises(RuntimeError, match="not open"):
        _ = uow.orders
    with pytest.raises(RuntimeError, match="not open"):
        _ = uow.capture_reservations


@pytest.mark.parametrize('factory', [FakeUnitOfWork, lambda: PostgresUnitOfWork(_Database())])
@pytest.mark.parametrize('name', ['customers', 'carpenters', 'quotes', 'orders', 'payments', 'tokens', 'capture_reservations', 'commit', 'rollback'])
def test_context_required_for_resolution_and_transaction_operations(factory, name):
    uow = factory()
    def access():
        value = getattr(uow, name)
        if name in ('commit', 'rollback'):
            value()
    with pytest.raises(RuntimeError, match='Transaction is not open'):
        access()
    with uow:
        assert getattr(uow, name) is not None
    with pytest.raises(RuntimeError, match='Transaction is not open'):
        access()
