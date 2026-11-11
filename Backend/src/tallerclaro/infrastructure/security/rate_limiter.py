"""Límites de uso persistentes con incremento atómico en PostgreSQL."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import psycopg


def window_start(now: datetime, window_seconds: int) -> datetime:
    """Inicio de la ventana fija que contiene ``now``."""
    if window_seconds < 1:
        raise ValueError("window_seconds must be positive")
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(
        epoch - (epoch % window_seconds), tz=timezone.utc
    )


class PostgresRateLimiter:
    """Implementa ``RateLimiter`` sobre ``tallerclaro.limite_consumo``.

    El incremento usa ``INSERT ... ON CONFLICT DO UPDATE`` para que dos
    peticiones concurrentes no puedan saltarse el límite. Nunca emite DELETE.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def retry_after(
        self, key: str, *, limit: int, window_seconds: int, now: datetime
    ) -> int | None:
        start = window_start(now, window_seconds)
        row = self._conn.execute(
            """
            SELECT contador, expira_en
            FROM tallerclaro.limite_consumo
            WHERE clave = %s AND ventana_inicio = %s
            """,
            (key, start),
        ).fetchone()
        if row is None or int(row[0]) < limit:
            return None
        remaining = (row[1] - now).total_seconds()
        return max(1, math.ceil(remaining))

    def hit(self, key: str, *, window_seconds: int, now: datetime) -> int:
        start = window_start(now, window_seconds)
        expires_at = start + timedelta(seconds=window_seconds)
        row = self._conn.execute(
            """
            INSERT INTO tallerclaro.limite_consumo
                (clave, ventana_inicio, contador, expira_en)
            VALUES (%s, %s, 1, %s)
            ON CONFLICT (clave, ventana_inicio)
            DO UPDATE SET contador = tallerclaro.limite_consumo.contador + 1
            RETURNING contador
            """,
            (key, start, expires_at),
        ).fetchone()
        return int(row[0])

    def reset(self, key: str, *, window_seconds: int, now: datetime) -> None:
        start = window_start(now, window_seconds)
        self._conn.execute(
            """
            UPDATE tallerclaro.limite_consumo
            SET contador = 0
            WHERE clave = %s AND ventana_inicio = %s
            """,
            (key, start),
        )
