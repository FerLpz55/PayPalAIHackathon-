"""Unidad de trabajo con PostgreSQL."""

from __future__ import annotations

from types import TracebackType

from tallerclaro.application.ports import CustomerTokenRepository, UnitOfWork
from tallerclaro.infrastructure.db.connection import Database
from tallerclaro.infrastructure.db.repositories import (
    PostgresCarpenterRepository,
    PostgresCustomerRepository,
    PostgresOrderRepository,
    PostgresPaymentRepository,
    PostgresQuoteRepository,
)
from tallerclaro.infrastructure.security.token_service import CustomerTokenService


class PostgresUnitOfWork:
    """Context manager que gestiona una transacción y los repositorios."""

    def __init__(
        self,
        database: Database,
        token_secret: str = "change-me-secret-min-32-chars-long",
        token_ttl_hours: int = 72,
    ) -> None:
        self._database = database
        self._token_secret = token_secret
        self._token_ttl_hours = token_ttl_hours
        self._conn = None
        self._tokens: CustomerTokenRepository | None = None

    def __enter__(self) -> UnitOfWork:
        self._conn = self._database.get_connection()
        self._customers = PostgresCustomerRepository(self._conn)
        self._carpenters = PostgresCarpenterRepository(self._conn)
        self._quotes = PostgresQuoteRepository(self._conn)
        self._orders = PostgresOrderRepository(self._conn)
        self._payments = PostgresPaymentRepository(self._conn)
        self._tokens = CustomerTokenService(
            self._conn,
            secret=self._token_secret,
            ttl_hours=self._token_ttl_hours,
        )
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
                self._tokens = None

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

    @property
    def tokens(self) -> CustomerTokenRepository:
        if self._tokens is None:
            raise RuntimeError("Transaction is not open")
        return self._tokens

    def get_connection(self):
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
