"""Contrato de configuración de PostgreSQL, sin conexiones ni secretos reales."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
from psycopg.conninfo import conninfo_to_dict

from tallerclaro.bootstrap.settings import Settings


def test_loads_database_url_from_dotenv(tmp_path):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://app:example@db.example:5432/workshop\n",
        encoding="utf-8",
    )

    params = conninfo_to_dict(Settings().database_dsn)

    assert params["host"] == "db.example"
    assert params["dbname"] == "workshop"
    assert params["user"] == "app"


@pytest.mark.parametrize("name", ["DATABASE_URL", "TALLERCLARO_DATABASE_URL"])
def test_accepts_database_url_environment_aliases(monkeypatch, name):
    monkeypatch.setenv(name, "postgres://app:example@process.example/workshop")

    assert conninfo_to_dict(Settings().database_dsn)["host"] == "process.example"


@pytest.mark.parametrize("source", ["environment", "dotenv"])
def test_database_url_wins_over_prefixed_alias_in_same_source(monkeypatch, tmp_path, source):
    values = {
        "DATABASE_URL": "postgres://app:example@primary.example/workshop",
        "TALLERCLARO_DATABASE_URL": "postgres://app:example@legacy.example/workshop",
    }
    if source == "environment":
        for name, value in values.items():
            monkeypatch.setenv(name, value)
    else:
        (tmp_path / ".env").write_text(
            "".join(f"{name}={value}\n" for name, value in values.items()),
            encoding="utf-8",
        )

    assert conninfo_to_dict(Settings().database_dsn)["host"] == "primary.example"


@pytest.mark.parametrize("name", ["DATABASE_URL", "TALLERCLARO_DATABASE_URL"])
def test_process_url_wins_over_dotenv_aliases(monkeypatch, tmp_path, name):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://app:example@file.example/workshop\n"
        "TALLERCLARO_DATABASE_URL=postgres://app:example@legacy-file.example/workshop\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(name, "postgres://app:example@process.example/workshop")

    assert conninfo_to_dict(Settings().database_dsn)["host"] == "process.example"


def test_explicit_database_url_wins_over_environment_and_dotenv(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgres://app:example@process.example/workshop")
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://app:example@file.example/workshop\n", encoding="utf-8"
    )

    settings = Settings(database_url="postgres://app:example@explicit.example/workshop")

    assert conninfo_to_dict(settings.database_dsn)["host"] == "explicit.example"


@pytest.mark.parametrize("password", ["example@2026", "example%402026"])
def test_password_at_sign_is_normalized_without_changing_original_url(password):
    url = f"postgres://app:{password}@127.0.0.1:15432/workshop?sslmode=require"

    settings = Settings(database_url=url)
    params = conninfo_to_dict(settings.database_dsn)

    assert params["password"] == "example@2026"
    assert params["host"] == "127.0.0.1"
    assert params["port"] == "15432"
    assert params["dbname"] == "workshop"
    assert params["sslmode"] == "require"
    assert settings.database_url == url


def test_individual_database_fields_remain_supported(monkeypatch):
    monkeypatch.setenv("TALLERCLARO_DATABASE_HOST", "fields.example")
    monkeypatch.setenv("TALLERCLARO_DATABASE_PORT", "5433")
    monkeypatch.setenv("TALLERCLARO_DATABASE_NAME", "workshop")
    monkeypatch.setenv("TALLERCLARO_DATABASE_USER", "app")
    monkeypatch.setenv("TALLERCLARO_DATABASE_PASSWORD", "example")
    monkeypatch.setenv("TALLERCLARO_DATABASE_SSL_MODE", "require")

    assert conninfo_to_dict(Settings().database_dsn) == {
        "host": "fields.example", "port": "5433", "dbname": "workshop",
        "user": "app", "password": "example", "sslmode": "require",
    }


def test_database_url_wins_over_individual_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://app:example@url.example/workshop")
    monkeypatch.setenv("TALLERCLARO_DATABASE_HOST", "fields.example")

    assert conninfo_to_dict(Settings().database_dsn)["host"] == "url.example"


def test_dotenv_can_be_disabled_explicitly(tmp_path):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://app:example@file.example/workshop\n", encoding="utf-8"
    )

    assert Settings(_env_file=None).database_url is None


def test_collection_is_isolated_from_invalid_local_settings(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    (tmp_path / ".env").write_text(
        "TALLERCLARO_DATABASE_PORT=not-a-port\n", encoding="utf-8"
    )
    environment = dict(os.environ, TALLERCLARO_DATABASE_PORT="not-a-port")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq", str(backend / "tests/api")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_supabase_pooler_url_parses_cleanly():
    url = (
        "postgresql://postgres.abcdefghijkl:my@secret@aws-0-us-east-1.pooler.supabase.com:5432/"
        "postgres?sslmode=require"
    )
    settings = Settings(database_url=url)
    params = conninfo_to_dict(settings.database_dsn)

    assert params["user"] == "postgres.abcdefghijkl"
    assert params["password"] == "my@secret"
    assert params["host"] == "aws-0-us-east-1.pooler.supabase.com"
    assert params["port"] == "5432"
    assert params["dbname"] == "postgres"
    assert params["sslmode"] == "require"


def test_postgres_uow_sets_serializable_isolation_on_enter():
    from unittest.mock import MagicMock
    from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_db.get_connection.return_value = mock_conn

    uow = PostgresUnitOfWork(mock_db)
    with uow:
        mock_conn.execute.assert_called_once_with(
            "SET LOCAL TRANSACTION ISOLATION LEVEL SERIALIZABLE"
        )
        uow.commit()

    mock_conn.commit.assert_called_once()
    mock_db.put_connection.assert_called_once_with(mock_conn)


def test_postgres_uow_returns_connection_if_isolation_setup_fails():
    from unittest.mock import MagicMock
    from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork

    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = RuntimeError("Supavisor error")
    mock_db.get_connection.return_value = mock_conn

    uow = PostgresUnitOfWork(mock_db)
    with pytest.raises(RuntimeError, match="Supavisor error"):
        with uow:
            pass

    mock_conn.rollback.assert_called_once()
    mock_db.put_connection.assert_called_once_with(mock_conn)

