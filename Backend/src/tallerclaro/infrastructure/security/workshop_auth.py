"""Verificación de credenciales del taller.

Aísla el uso de bcrypt de la resolución HTTP de credenciales. La validación de
la configuración es la misma que se usa al autenticar, de modo que el arranque
y las peticiones comparten una única implementación criptográfica.
"""

from __future__ import annotations

import secrets

import bcrypt

from tallerclaro.bootstrap.settings import Settings

_CONFIGURATION_PROBE = b"configuration-check"
_INVALID_HASH_MESSAGE = "A valid workshop bcrypt password hash is required"


def is_valid_password_hash(password_hash: str) -> bool:
    """Indica si el valor es un hash bcrypt utilizable por ``checkpw``."""
    if not password_hash:
        return False
    try:
        bcrypt.checkpw(_CONFIGURATION_PROBE, password_hash.encode("ascii"))
    except (ValueError, UnicodeError, TypeError):
        return False
    return True


def verify_workshop_credentials(username: str, password: str, settings: Settings) -> bool:
    """Comprueba usuario y contraseña contra la configuración del taller."""
    try:
        valid_user = secrets.compare_digest(username, settings.workshop_username)
    except TypeError:
        return False
    try:
        valid_password = bcrypt.checkpw(
            password.encode("utf-8"), settings.workshop_password_hash.encode("ascii")
        )
    except (ValueError, UnicodeError, TypeError):
        valid_password = False
    return valid_user and valid_password


def ensure_workshop_auth_configured(settings: Settings) -> None:
    """Falla el arranque si el hash configurado no es un bcrypt válido."""
    if not is_valid_password_hash(settings.workshop_password_hash):
        raise RuntimeError(_INVALID_HASH_MESSAGE)
