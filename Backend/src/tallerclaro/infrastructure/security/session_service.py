"""Sesiones opacas del taller con hash persistido y caducidad deslizante."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import psycopg

from tallerclaro.domain.entities import CarpenterId


def credential_fingerprint(password_hash: str) -> str:
    """Huella del hash bcrypt vigente; cambiarlo invalida las sesiones emitidas."""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WorkshopSessionService:
    """Implementa ``WorkshopSessionRepository`` sobre PostgreSQL.

    El token opaco (256 bits) solo se devuelve al crear la sesión. En la base de
    datos se guarda su SHA-256, nunca el valor original.
    """

    def __init__(
        self,
        conn: psycopg.Connection,
        *,
        credential_fingerprint: str,
        idle_minutes: int = 30,
        absolute_hours: int = 8,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._conn = conn
        self._credential_fingerprint = credential_fingerprint
        self._idle_minutes = idle_minutes
        self._absolute_hours = absolute_hours
        self._clock = clock if clock is not None else lambda: datetime.now(timezone.utc)

    def create(self, carpenter_id: CarpenterId) -> str:
        token = secrets.token_urlsafe(32)
        now = self._clock()
        expires_at = now + timedelta(hours=self._absolute_hours)
        self._conn.execute(
            """
            INSERT INTO tallerclaro.sesion_taller
                (id_carpintero, token_hash, credencial_huella,
                 fecha_creacion, ultimo_uso, fecha_expiracion)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                int(carpenter_id),
                _token_hash(token),
                self._credential_fingerprint,
                now,
                now,
                expires_at,
            ),
        )
        return token

    def verify(self, token: str) -> CarpenterId | None:
        if not token:
            return None
        now = self._clock()
        idle_cutoff = now - timedelta(minutes=self._idle_minutes)
        row = self._conn.execute(
            """
            UPDATE tallerclaro.sesion_taller
            SET ultimo_uso = %s
            WHERE token_hash = %s
              AND revocada_en IS NULL
              AND credencial_huella = %s
              AND fecha_expiracion > %s
              AND ultimo_uso > %s
            RETURNING id_carpintero
            """,
            (now, _token_hash(token), self._credential_fingerprint, now, idle_cutoff),
        ).fetchone()
        if row is None:
            return None
        return CarpenterId(int(row[0]))

    def revoke(self, token: str) -> bool:
        if not token:
            return False
        cursor = self._conn.execute(
            """
            UPDATE tallerclaro.sesion_taller
            SET revocada_en = %s
            WHERE token_hash = %s
              AND revocada_en IS NULL
            """,
            (self._clock(), _token_hash(token)),
        )
        return bool(cursor.rowcount)

    def revoke_all(self, carpenter_id: CarpenterId) -> int:
        cursor = self._conn.execute(
            """
            UPDATE tallerclaro.sesion_taller
            SET revocada_en = %s
            WHERE id_carpintero = %s
              AND revocada_en IS NULL
            """,
            (self._clock(), int(carpenter_id)),
        )
        return int(cursor.rowcount or 0)
