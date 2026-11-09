"""Cookies de sesión y protección CSRF de la capa HTTP.

Las cookies usan el prefijo ``__Host-``: el navegador exige ``Secure``, ``Path=/``
y la ausencia de ``Domain``. El token de sesión es ``HttpOnly``; el token CSRF es
legible por el JavaScript del mismo origen para enviarlo en ``X-CSRF-Token``.
"""

from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import Response

from tallerclaro.application.exceptions import ForbiddenError
from tallerclaro.bootstrap.settings import Settings

SESSION_COOKIE_NAME = "__Host-tallerclaro_session"
CSRF_COOKIE_NAME = "__Host-tallerclaro_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_COOKIE_PATH = "/"
_COOKIE_SAME_SITE = "lax"


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def read_session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)


def ensure_allowed_origin(request: Request, settings: Settings) -> None:
    """Rechaza orígenes no autorizados cuando el navegador envía ``Origin``."""
    origin = request.headers.get("origin")
    if not origin:
        return
    allowed = settings.cors_origins
    if "*" in allowed and not settings.is_release:
        return
    if origin not in allowed:
        raise ForbiddenError("Origin not allowed")


def enforce_csrf(request: Request, settings: Settings) -> None:
    """Exige doble envío de token CSRF en métodos que cambian estado."""
    if request.method.upper() in _SAFE_METHODS:
        return
    ensure_allowed_origin(request, settings)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token:
        raise ForbiddenError("CSRF token required")
    if not secrets.compare_digest(cookie_token, header_token):
        raise ForbiddenError("Invalid CSRF token")


def set_session_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    max_age = settings.workshop_session_absolute_hours * 3600
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=max_age,
        path=_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=_COOKIE_SAME_SITE,
    )
    set_csrf_cookie(response, csrf_token, settings)
    response.headers["Cache-Control"] = "no-store"


def set_csrf_cookie(response: Response, csrf_token: str, settings: Settings) -> None:
    max_age = settings.workshop_session_absolute_hours * 3600
    response.set_cookie(
        CSRF_COOKIE_NAME,
        csrf_token,
        max_age=max_age,
        path=_COOKIE_PATH,
        secure=True,
        httponly=False,
        samesite=_COOKIE_SAME_SITE,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path=_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite=_COOKIE_SAME_SITE,
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path=_COOKIE_PATH,
        secure=True,
        httponly=False,
        samesite=_COOKIE_SAME_SITE,
    )
    response.headers["Cache-Control"] = "no-store"
