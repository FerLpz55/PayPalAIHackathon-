"""Límites de abuso aplicados desde la capa HTTP."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request

from tallerclaro.application.exceptions import RateLimitedError
from tallerclaro.application.interfaces import UnitOfWork
from tallerclaro.bootstrap.settings import Settings

LOGIN_FAILURES_LIMIT = 5
LOGIN_FAILURES_WINDOW_SECONDS = 15 * 60

QUOTE_CREATION_LIMIT = 5
QUOTE_CREATION_WINDOW_SECONDS = 60

GENERATION_LIMIT = 5
GENERATION_WINDOW_SECONDS = 10 * 60

GENERATION_WORKSHOP_BUDGET = 100
GENERATION_WORKSHOP_WINDOW_SECONDS = 60 * 60

CATALOG_LIMIT = 20
CATALOG_WINDOW_SECONDS = 60


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def client_ip(request: Request, settings: Settings) -> str:
    """Solo usa X-Forwarded-For cuando el proxy propio está configurado como confiable."""
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client is not None else "unknown"


def actor_key(principal) -> str:
    """Clave estable por actor: cliente o taller autenticado."""
    if principal.is_workshop:
        return f"workshop:{principal.carpenter_id}"
    return f"customer:{principal.customer_id}"


def login_keys(username: str, ip: str) -> tuple[str, str]:
    return (
        f"login:user:{username.strip().lower()}",
        f"login:ip:{ip}",
    )


def enforce_login_allowed(
    uow: UnitOfWork, username: str, ip: str, *, now: datetime | None = None
) -> None:
    moment = now or utcnow()
    with uow:
        for key in login_keys(username, ip):
            retry = uow.rate_limits.retry_after(
                key,
                limit=LOGIN_FAILURES_LIMIT,
                window_seconds=LOGIN_FAILURES_WINDOW_SECONDS,
                now=moment,
            )
            if retry is not None:
                raise RateLimitedError(retry, "Too many failed login attempts")


def record_login_failure(
    uow: UnitOfWork, username: str, ip: str, *, now: datetime | None = None
) -> None:
    moment = now or utcnow()
    for key in login_keys(username, ip):
        uow.execute_sql(
            lambda active, key=key: active.rate_limits.hit(
                key,
                window_seconds=LOGIN_FAILURES_WINDOW_SECONDS,
                now=moment,
            )
        )


def reset_login_failures(
    uow: UnitOfWork, username: str, ip: str, *, now: datetime | None = None
) -> None:
    moment = now or utcnow()
    for key in login_keys(username, ip):
        uow.execute_sql(
            lambda active, key=key: active.rate_limits.reset(
                key,
                window_seconds=LOGIN_FAILURES_WINDOW_SECONDS,
                now=moment,
            )
        )


def _seconds_left(now: datetime, window_seconds: int) -> int:
    """Segundos que faltan para que empiece la siguiente ventana fija."""
    epoch = int(now.timestamp())
    return max(1, window_seconds - (epoch % window_seconds))


def _enforce_and_hit(
    uow: UnitOfWork,
    keys: list[tuple[str, int, int]],
    *,
    now: datetime | None = None,
    message: str = "Too many requests",
) -> None:
    """Incrementa de forma atómica y rechaza si el contador supera el límite.

    ``hit`` usa ``INSERT ... ON CONFLICT DO UPDATE`` en PostgreSQL, así que dos
    peticiones concurrentes nunca pueden saltarse el límite por una lectura
    previa obsoleta. El consumo del intento rechazado también cuenta.
    """
    moment = now or utcnow()
    for key, limit, window_seconds in keys:
        count = uow.execute_sql(
            lambda active, key=key, window=window_seconds: active.rate_limits.hit(
                key,
                window_seconds=window,
                now=moment,
            )
        )
        if count > limit:
            raise RateLimitedError(_seconds_left(moment, window_seconds), message)


def enforce_quote_creation(
    uow: UnitOfWork, ip: str, *, now: datetime | None = None
) -> None:
    _enforce_and_hit(
        uow,
        [(f"quotes:create:ip:{ip}", QUOTE_CREATION_LIMIT, QUOTE_CREATION_WINDOW_SECONDS)],
        now=now,
    )


def enforce_quote_generation(
    uow: UnitOfWork,
    quote_id: int,
    workshop_id: int,
    *,
    now: datetime | None = None,
) -> None:
    _enforce_and_hit(
        uow,
        [
            (f"quotes:generate:{quote_id}", GENERATION_LIMIT, GENERATION_WINDOW_SECONDS),
            (
                f"quotes:generate:workshop:{workshop_id}",
                GENERATION_WORKSHOP_BUDGET,
                GENERATION_WORKSHOP_WINDOW_SECONDS,
            ),
        ],
        now=now,
    )


def enforce_catalog_lookup(
    uow: UnitOfWork, actor: str, *, now: datetime | None = None
) -> None:
    _enforce_and_hit(
        uow,
        [(f"catalog:{actor}", CATALOG_LIMIT, CATALOG_WINDOW_SECONDS)],
        now=now,
    )
