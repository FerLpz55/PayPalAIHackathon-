"""Reintento acotado de conflictos SERIALIZABLE dentro de fases SQL."""

import psycopg
import pytest

from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork


class _StubConnection:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def execute(self, sql: str) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class _StubDatabase:
    def __init__(self) -> None:
        self.connections: list[_StubConnection] = []

    def get_connection(self) -> _StubConnection:
        connection = _StubConnection()
        self.connections.append(connection)
        return connection

    def put_connection(self, connection: _StubConnection) -> None:
        return None


def test_execute_sql_retries_serialization_failures_with_new_connections():
    database = _StubDatabase()
    uow = PostgresUnitOfWork(database)
    attempts = []

    def operation(active_uow):
        attempts.append(1)
        if len(attempts) < 3:
            raise psycopg.errors.SerializationFailure("could not serialize")
        return "ok"

    assert uow.execute_sql(operation) == "ok"
    assert len(attempts) == 3
    assert len(database.connections) == 3
    # Los dos intentos fallidos revierten; solo el último confirma.
    assert [conn.commits for conn in database.connections] == [0, 0, 1]
    assert [conn.rollbacks for conn in database.connections] == [1, 1, 0]


def test_execute_sql_stops_after_configured_attempts():
    database = _StubDatabase()
    uow = PostgresUnitOfWork(database)

    def operation(active_uow):
        raise psycopg.errors.SerializationFailure("could not serialize")

    with pytest.raises(psycopg.errors.SerializationFailure):
        uow.execute_sql(operation, attempts=2)
    assert len(database.connections) == 2


def test_execute_sql_does_not_retry_other_errors():
    database = _StubDatabase()
    uow = PostgresUnitOfWork(database)

    def operation(active_uow):
        raise ValueError("business rule")

    with pytest.raises(ValueError, match="business rule"):
        uow.execute_sql(operation)
    assert len(database.connections) == 1


def test_execute_sql_rejects_invalid_attempt_count():
    uow = PostgresUnitOfWork(_StubDatabase())
    with pytest.raises(ValueError):
        uow.execute_sql(lambda active_uow: None, attempts=0)


def test_fake_unit_of_work_commits_sql_phases():
    from tests.fakes import FakeUnitOfWork

    uow = FakeUnitOfWork()
    assert uow.execute_sql(lambda active_uow: "result") == "result"
