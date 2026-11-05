from unittest.mock import MagicMock, patch

import bcrypt
import pytest
from fastapi.testclient import TestClient

from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.db.connection import Database


def test_failed_pool_start_closes_pool():
    pool = MagicMock()
    pool.wait.side_effect = RuntimeError("unavailable")
    with patch("tallerclaro.infrastructure.db.connection.ConnectionPool", return_value=pool):
        with pytest.raises(RuntimeError, match="unavailable"):
            Database(Settings()).connect()
    pool.close.assert_called_once()


def test_database_connection_failure_prevents_startup():
    from tallerclaro.main import create_app

    settings = Settings(workshop_password_hash=bcrypt.hashpw(b"test", bcrypt.gensalt(rounds=4)).decode())
    with patch("tallerclaro.main.Database") as database:
        database.return_value.connect.side_effect = RuntimeError("unavailable")
        with pytest.raises(RuntimeError, match="unavailable"):
            with TestClient(create_app(settings=settings)):
                pass
