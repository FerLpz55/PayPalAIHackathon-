"""Conexión a PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg_pool import ConnectionPool, PoolClosed, PoolTimeout

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.exceptions import ServiceUnavailableError

_CONNECT_WAIT_TIMEOUT_SECONDS = 10


class DatabaseUnavailableError(ServiceUnavailableError):
    """La base de datos no está disponible; se traduce a HTTP 503."""

    def __init__(self, message: str = "Database is temporarily unavailable") -> None:
        super().__init__(message=message)


@dataclass(frozen=True)
class DatabasePrivileges:
    """Resultado de solo lectura para auditar el rol efectivo."""

    current_user: str
    is_superuser: bool
    tables_with_delete: tuple[str, ...]


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
            timeout=self._settings.database_pool_acquire_timeout_seconds,
            max_idle=self._settings.database_pool_max_idle_seconds,
            check=ConnectionPool.check_connection,
            kwargs={"prepare_threshold": None},
        )
        try:
            self._pool.open()
            self._pool.wait(timeout=_CONNECT_WAIT_TIMEOUT_SECONDS)
            self.check_connection()
        except Exception:
            self._pool.close()
            self._pool = None
            raise

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def check_connection(self) -> None:
        """Valida que el pool entregue una conexión utilizable."""
        if self._pool is None:
            raise DatabaseUnavailableError("Database pool is not connected")
        try:
            with self._pool.connection(
                timeout=self._settings.database_pool_acquire_timeout_seconds
            ) as conn:
                conn.execute("SELECT 1")
        except (PoolTimeout, PoolClosed, psycopg.Error) as exc:
            raise DatabaseUnavailableError() from exc

    def inspect_privileges(self) -> DatabasePrivileges:
        """Consulta el rol efectivo y las tablas donde puede borrar (solo lectura)."""
        if self._pool is None:
            raise DatabaseUnavailableError("Database pool is not connected")
        with self._pool.connection(
            timeout=self._settings.database_pool_acquire_timeout_seconds
        ) as conn:
            row = conn.execute(
                "SELECT current_user, current_setting('is_superuser') = 'on'"
            ).fetchone()
            tables = conn.execute(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'tallerclaro'
                  AND c.relkind = 'r'
                  AND has_table_privilege(current_user, c.oid, 'DELETE')
                ORDER BY c.relname
                """
            ).fetchall()
        return DatabasePrivileges(
            current_user=str(row[0]),
            is_superuser=bool(row[1]),
            tables_with_delete=tuple(str(table[0]) for table in tables),
        )

    def get_connection(self) -> psycopg.Connection:
        if self._pool is None:
            raise DatabaseUnavailableError("Database pool is not connected")
        try:
            return self._pool.getconn(
                timeout=self._settings.database_pool_acquire_timeout_seconds
            )
        except (PoolTimeout, PoolClosed, psycopg.Error) as exc:
            raise DatabaseUnavailableError() from exc

    def put_connection(self, conn: psycopg.Connection) -> None:
        if self._pool is None:
            # El pool se cerró mientras la petición estaba en curso; no hay a quién devolverla.
            try:
                conn.close()
            except Exception:
                pass
            return
        self._pool.putconn(conn)
