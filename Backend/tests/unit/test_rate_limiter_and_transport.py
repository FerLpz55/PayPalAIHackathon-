"""Límites atómicos, cuerpo máximo y mapeo de errores de transporte."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from tallerclaro.application.exceptions import RateLimitedError
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.infrastructure.security.rate_limiter import (
    PostgresRateLimiter,
    window_start,
)
from tallerclaro.presentation.http.exception_handlers import _domain_error_to_status

MOMENT = datetime(2026, 11, 9, 12, 7, 30, tzinfo=timezone.utc)


def test_window_start_is_fixed_and_aligned():
    assert window_start(MOMENT, 60) == datetime(
        2026, 11, 9, 12, 7, tzinfo=timezone.utc
    )
    assert window_start(MOMENT, 900) == datetime(
        2026, 11, 9, 12, 0, tzinfo=timezone.utc
    )


def test_window_start_rejects_non_positive_window():
    with pytest.raises(ValueError):
        window_start(MOMENT, 0)


def test_hit_uses_atomic_insert_on_conflict_and_returns_counter():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (4,)

    value = PostgresRateLimiter(conn).hit("key", window_seconds=60, now=MOMENT)

    sql, params = conn.execute.call_args.args
    assert "INSERT INTO tallerclaro.limite_consumo" in sql
    assert "ON CONFLICT (clave, ventana_inicio)" in sql
    assert "DO UPDATE SET contador = tallerclaro.limite_consumo.contador + 1" in sql
    assert "DELETE" not in sql.upper()
    assert value == 4
    assert params[0] == "key"
    assert params[1] == window_start(MOMENT, 60)


def test_retry_after_is_none_below_limit_and_positive_at_limit():
    conn = MagicMock()
    limiter = PostgresRateLimiter(conn)

    conn.execute.return_value.fetchone.return_value = (4, MOMENT)
    assert limiter.retry_after("key", limit=5, window_seconds=60, now=MOMENT) is None

    expires = datetime(2026, 11, 9, 12, 8, tzinfo=timezone.utc)
    conn.execute.return_value.fetchone.return_value = (5, expires)
    retry = limiter.retry_after("key", limit=5, window_seconds=60, now=MOMENT)
    assert retry == 30


def test_retry_after_ignores_missing_window():
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    assert (
        PostgresRateLimiter(conn).retry_after(
            "key", limit=5, window_seconds=60, now=MOMENT
        )
        is None
    )


def test_reset_uses_update_not_delete():
    conn = MagicMock()
    PostgresRateLimiter(conn).reset("key", window_seconds=60, now=MOMENT)

    sql = conn.execute.call_args.args[0]
    assert "UPDATE tallerclaro.limite_consumo" in sql
    assert "SET contador = 0" in sql
    assert "DELETE" not in sql.upper()


def test_rate_limited_and_payload_errors_map_to_expected_status():
    assert _domain_error_to_status(RateLimitedError(5)) == 429


def test_rate_limited_error_keeps_positive_retry_after():
    assert RateLimitedError(0).retry_after == 1
    assert RateLimitedError(12).retry_after == 12


def test_retry_after_header_is_returned_for_rate_limited_errors():
    from tallerclaro.main import create_app

    from tallerclaro.presentation.http.exception_handlers import domain_error_handler

    app = create_app(settings=Settings(), ai_service=MagicMock(), payment_processor=MagicMock())
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "client": ("testclient", 123),
        "scheme": "http",
        "root_path": "",
        "app": app,
    }
    from starlette.requests import Request

    response = domain_error_handler(Request(scope), RateLimitedError(9))
    assert response.status_code == 429
    assert response.headers["retry-after"] == "9"


def test_content_length_over_limit_is_rejected_without_reading_body():
    import asyncio

    from tallerclaro.presentation.http.middleware import RequestBodyLimitMiddleware

    called = {"app": False}

    async def inner_app(scope, receive, send):
        called["app"] = True

    sent = []

    async def receive():  # pragma: no cover - no debe leerse el cuerpo
        raise AssertionError("body must not be read when Content-Length is too large")

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(inner_app, max_body_bytes=1024)
    asyncio.run(
        middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/",
                "headers": [(b"content-length", b"99999")],
            },
            receive,
            send,
        )
    )

    assert called["app"] is False
    assert sent[0]["status"] == 413
    assert b"PAYLOAD_TOO_LARGE" in sent[1]["body"]


def test_chunked_body_without_content_length_is_rejected_while_reading():
    import asyncio
    import json

    from tallerclaro.presentation.http.middleware import RequestBodyLimitMiddleware

    async def inner_app(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    chunks = [
        {"type": "http.request", "body": b"x" * 600, "more_body": True},
        {"type": "http.request", "body": b"x" * 600, "more_body": False},
    ]

    async def receive():
        return chunks.pop(0)

    sent = []

    async def send(message):
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(inner_app, max_body_bytes=1024)
    asyncio.run(
        middleware(
            {"type": "http", "method": "POST", "path": "/", "headers": []},
            receive,
            send,
        )
    )

    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["code"] == "PAYLOAD_TOO_LARGE"


def test_non_http_scope_is_forwarded_untouched():
    import asyncio

    from tallerclaro.presentation.http.middleware import RequestBodyLimitMiddleware

    seen = {}

    async def inner_app(scope, receive, send):
        seen["scope"] = scope

    middleware = RequestBodyLimitMiddleware(inner_app, max_body_bytes=1024)
    scope = {"type": "lifespan"}

    async def receive():  # pragma: no cover
        return {"type": "lifespan.startup"}

    async def send(message):  # pragma: no cover
        return None

    asyncio.run(middleware(scope, receive, send))
    assert seen["scope"] is scope
