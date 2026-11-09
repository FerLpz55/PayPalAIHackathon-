"""Pool de conexiones: configuración, verificación y errores controlados."""

from unittest.mock import MagicMock, patch

import psycopg
import pytest
from psycopg_pool import PoolClosed, PoolTimeout

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.db.connection import (
    Database,
    DatabaseUnavailableError,
)


def _database() -> Database:
    return Database(Settings())


def test_pool_is_configured_with_health_check_and_idle_expiry():
    pool = MagicMock()
    with patch(
        "tallerclaro.infrastructure.db.connection.ConnectionPool", return_value=pool
    ) as factory:
        _database().connect()

    kwargs = factory.call_args.kwargs
    assert kwargs["check"] is not None
    assert kwargs["max_idle"] == 300
    assert kwargs["timeout"] == 10
    assert kwargs["kwargs"] == {"prepare_threshold": None}


def test_connect_verifies_connection_after_waiting():
    pool = MagicMock()
    with patch(
        "tallerclaro.infrastructure.db.connection.ConnectionPool", return_value=pool
    ):
        _database().connect()
    connection_context = pool.connection.return_value.__enter__.return_value
    connection_context.execute.assert_called_once_with("SELECT 1")


def test_check_connection_translates_pool_timeout():
    database = _database()
    database._pool = MagicMock()
    database._pool.connection.side_effect = PoolTimeout("timed out")
    with pytest.raises(DatabaseUnavailableError):
        database.check_connection()


def test_check_connection_translates_psycopg_error():
    database = _database()
    database._pool = MagicMock()
    connection = database._pool.connection.return_value.__enter__.return_value
    connection.execute.side_effect = psycopg.OperationalError("reset")
    with pytest.raises(DatabaseUnavailableError):
        database.check_connection()


def test_check_connection_without_pool_is_controlled_error():
    with pytest.raises(DatabaseUnavailableError):
        _database().check_connection()


@pytest.mark.parametrize("error", [PoolTimeout("timed out"), PoolClosed("closed")])
def test_get_connection_translates_pool_errors(error):
    database = _database()
    database._pool = MagicMock()
    database._pool.getconn.side_effect = error
    with pytest.raises(DatabaseUnavailableError):
        database.get_connection()


def test_put_connection_returns_connection_to_pool():
    database = _database()
    database._pool = MagicMock()
    connection = MagicMock()
    database.put_connection(connection)
    database._pool.putconn.assert_called_once_with(connection)


def test_put_connection_closes_when_pool_was_closed():
    database = _database()
    connection = MagicMock()
    database.put_connection(connection)
    connection.close.assert_called_once_with()


def test_database_unavailable_maps_to_503():
    from tallerclaro.presentation.http.exception_handlers import _domain_error_to_status

    assert _domain_error_to_status(DatabaseUnavailableError()) == 503


def test_inspect_privileges_reports_delete_grants():
    database = _database()
    database._pool = MagicMock()
    connection = database._pool.connection.return_value.__enter__.return_value
    connection.execute.side_effect = [
        MagicMock(fetchone=lambda: ("tallerclaro_app", False)),
        MagicMock(fetchall=lambda: [("pedido",), ("pago",)]),
    ]

    privileges = database.inspect_privileges()

    assert privileges.current_user == "tallerclaro_app"
    assert privileges.is_superuser is False
    assert privileges.tables_with_delete == ("pedido", "pago")


def test_release_privilege_guard_rejects_superuser_and_delete():
    from tallerclaro.infrastructure.db.connection import DatabasePrivileges
    from tallerclaro.main import _enforce_minimal_database_privileges

    superuser = MagicMock()
    superuser.inspect_privileges.return_value = DatabasePrivileges("postgres", True, ())
    with pytest.raises(RuntimeError, match="non-superuser"):
        _enforce_minimal_database_privileges(superuser)

    with_delete = MagicMock()
    with_delete.inspect_privileges.return_value = DatabasePrivileges(
        "tallerclaro_app", False, ("pedido",)
    )
    with pytest.raises(RuntimeError, match="DELETE"):
        _enforce_minimal_database_privileges(with_delete)

    clean = MagicMock()
    clean.inspect_privileges.return_value = DatabasePrivileges(
        "tallerclaro_app", False, ()
    )
    _enforce_minimal_database_privileges(clean)
