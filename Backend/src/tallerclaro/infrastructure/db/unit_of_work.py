"""Unidad de trabajo con PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Any

from tallerclaro.application.interfaces import CustomerTokenRepository, UnitOfWork
from tallerclaro.infrastructure.db.connection import Database
from tallerclaro.infrastructure.db.repositories import (
    PostgresCaptureReservationRepository,
    PostgresCarpenterRepository,
    PostgresCustomerRepository,
    PostgresOrderRepository,
    PostgresPaymentRepository,
    PostgresQuoteRepository,
)
from tallerclaro.infrastructure.security.token_service import CustomerTokenService


@dataclass
class _TransactionFrame:
    conn: Any
    customers: PostgresCustomerRepository
    carpenters: PostgresCarpenterRepository
    quotes: PostgresQuoteRepository
    orders: PostgresOrderRepository
    capture_reservations: PostgresCaptureReservationRepository
    payments: PostgresPaymentRepository
    tokens: CustomerTokenRepository
    committed: bool = False


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
        self._frames: list[_TransactionFrame] = []
        self._conn = None

    def _active_frame(self) -> _TransactionFrame:
        if not self._frames:
            raise RuntimeError("Transaction is not open")
        return self._frames[-1]

    def __enter__(self) -> UnitOfWork:
        conn = self._database.get_connection()
        if hasattr(conn, "execute"):
            try:
                conn.execute("SET LOCAL TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            except Exception:
                conn.rollback()
                self._database.put_connection(conn)
                raise
        frame = _TransactionFrame(
            conn=conn,
            customers=PostgresCustomerRepository(conn),
            carpenters=PostgresCarpenterRepository(conn),
            quotes=PostgresQuoteRepository(conn),
            orders=PostgresOrderRepository(conn),
            capture_reservations=PostgresCaptureReservationRepository(conn),
            payments=PostgresPaymentRepository(conn),
            tokens=CustomerTokenService(
                conn,
                secret=self._token_secret,
                ttl_hours=self._token_ttl_hours,
            ),
            committed=False,
        )
        self._frames.append(frame)
        self._conn = conn
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self._frames:
            return
        frame = self._frames.pop()
        self._conn = self._frames[-1].conn if self._frames else None
        try:
            if exc_type is not None or not frame.committed:
                frame.conn.rollback()
        finally:
            self._database.put_connection(frame.conn)

    @property
    def customers(self) -> PostgresCustomerRepository:
        return self._active_frame().customers

    @property
    def carpenters(self) -> PostgresCarpenterRepository:
        return self._active_frame().carpenters

    @property
    def quotes(self) -> PostgresQuoteRepository:
        return self._active_frame().quotes

    @property
    def orders(self) -> PostgresOrderRepository:
        return self._active_frame().orders

    @property
    def capture_reservations(self) -> PostgresCaptureReservationRepository:
        return self._active_frame().capture_reservations

    @property
    def payments(self) -> PostgresPaymentRepository:
        return self._active_frame().payments

    @property
    def tokens(self) -> CustomerTokenRepository:
        return self._active_frame().tokens

    def get_connection(self):
        """Expone la conexión activa."""
        return self._active_frame().conn

    def commit(self) -> None:
        frame = self._active_frame()
        frame.conn.commit()
        frame.committed = True

    def rollback(self) -> None:
        frame = self._active_frame()
        frame.conn.rollback()
        frame.committed = False
