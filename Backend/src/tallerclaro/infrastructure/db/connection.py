"""Conexión a PostgreSQL."""

from __future__ import annotations

import psycopg
from psycopg_pool import ConnectionPool

from tallerclaro.bootstrap.settings import Settings


class Database:
    """Gestiona el pool de conexiones a PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: ConnectionPool | None = None

    def connect(self) -> None:
        self._pool = ConnectionPool(
            conninfo=self._settings.database_dsn,
            min_size=self._settings.database_pool_min_size,
            max_size=self._settings.database_pool_max_size,
            open=False,
            kwargs={"prepare_threshold": None},
        )
        try:
            self._pool.open()
            self._pool.wait(timeout=2)
        except Exception:
            # El pool permanecerá cerrado; las operaciones fallarán claramente.
            self._pool = None
            raise

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()

    def get_connection(self) -> psycopg.Connection:
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return self._pool.getconn()

    def put_connection(self, conn: psycopg.Connection) -> None:
        if self._pool is None:
            raise RuntimeError("Database not connected")
        self._pool.putconn(conn)
