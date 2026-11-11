"""Servicio de tokens de enlace de cliente."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import psycopg

from tallerclaro.domain.entities import CustomerId, QuoteId


class CustomerTokenService:
    """Genera y verifica tokens de enlace de cliente."""

    def __init__(self, conn: psycopg.Connection, secret: str, ttl_hours: int = 72, *, clock: Callable[[], datetime] | None = None) -> None:
        self._conn = conn
        self._secret = secret.encode("utf-8")
        self._ttl_hours = ttl_hours
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def create(self, customer_id: CustomerId, quote_id: QuoteId) -> str:
        raw = secrets.token_urlsafe(32)
        token_hash = self._hash(raw)
        expiration = self._clock() + timedelta(hours=self._ttl_hours)
        self._conn.execute(
            """
            INSERT INTO tallerclaro.cliente_token
                (id_cliente, id_cotizacion, token_hash, fecha_expiracion)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (token_hash) DO UPDATE SET
                id_cliente = EXCLUDED.id_cliente,
                id_cotizacion = EXCLUDED.id_cotizacion,
                fecha_expiracion = EXCLUDED.fecha_expiracion
            """,
            (customer_id, quote_id, token_hash, expiration),
        )
        return raw

    def verify(self, token: str) -> tuple[CustomerId, QuoteId] | None:
        token_hash = self._hash(token)
        row = self._conn.execute(
            """
            SELECT id_cliente, id_cotizacion, fecha_expiracion, usado
            FROM tallerclaro.cliente_token
            WHERE token_hash = %s
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        if row[2] < self._clock() or row[3]:
            return None
        return CustomerId(row[0]), QuoteId(row[1])

    def _hash(self, token: str) -> str:
        return hmac.new(self._secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
