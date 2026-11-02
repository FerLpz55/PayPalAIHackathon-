"""Unidad de trabajo con PostgreSQL."""

from __future__ import annotations

from types import TracebackType

from tallerclaro.application.ports import UnitOfWork
from tallerclaro.infrastructure.db.connection import Database
from tallerclaro.infrastructure.db.repositories import (
    PostgresCarpenterRepository,
    PostgresCustomerRepository,
    PostgresOrderRepository,
    PostgresPaymentRepository,
    PostgresQuoteRepository,
)


class PostgresUnitOfWork:
    """Context manager que gestiona una transacción y los repositorios."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._conn = None

    def __enter__(self) -> UnitOfWork:
        self._conn = self._database.get_connection()
        self._customers = PostgresCustomerRepository(self._conn)
        self._carpenters = PostgresCarpenterRepository(self._conn)
        self._quotes = PostgresQuoteRepository(self._conn)
        self._orders = PostgresOrderRepository(self._conn)
        self._payments = PostgresPaymentRepository(self._conn)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._conn is not None:
            if exc_type is not None:
                self._conn.rollback()
            try:
                self._database.put_connection(self._conn)
            finally:
                self._conn = None

    @property
    def customers(self) -> PostgresCustomerRepository:
        return self._customers

    @property
    def carpenters(self) -> PostgresCarpenterRepository:
        return self._carpenters

    @property
    def quotes(self) -> PostgresQuoteRepository:
        return self._quotes

    @property
    def orders(self) -> PostgresOrderRepository:
        return self._orders

    @property
    def payments(self) -> PostgresPaymentRepository:
        return self._payments

    def get_connection(self) -> psycopg.Connection:
        """Expone la conexión para dependencias que la necesiten (ej. tokens)."""
        if self._conn is None:
            raise RuntimeError("No active connection")
        return self._conn

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def rollback(self) -> None:
        if self._conn is not None:
            self._conn.rollback()
