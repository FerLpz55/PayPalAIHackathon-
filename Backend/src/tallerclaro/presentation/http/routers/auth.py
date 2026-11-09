"""Endpoints de sesión del taller."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from tallerclaro.application.interfaces import UnitOfWork
from tallerclaro.application.use_cases import (
    EndWorkshopSession,
    ResolveWorkshopSession,
    StartWorkshopSession,
)
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.presentation.http.dependencies import (
    authenticate_workshop_credentials,
    get_settings,
    get_unit_of_work,
)
from tallerclaro.presentation.http.rate_limits import (
    client_ip,
    enforce_login_allowed,
    record_login_failure,
    reset_login_failures,
)
from tallerclaro.presentation.http.schemas.auth import LoginRequest, SessionResponse
from tallerclaro.presentation.http.session_cookies import (
    CSRF_COOKIE_NAME,
    clear_session_cookies,
    ensure_allowed_origin,
    enforce_csrf,
    new_csrf_token,
    read_session_token,
    set_csrf_cookie,
    set_session_cookies,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _session_payload(
    settings: Settings, *, carpenter_id: int, csrf_token: str
) -> SessionResponse:
    return SessionResponse(
        authenticated=True,
        carpenter_id=carpenter_id,
        username=settings.workshop_username,
        csrf_token=csrf_token,
        idle_timeout_seconds=settings.workshop_session_idle_minutes * 60,
        absolute_timeout_seconds=settings.workshop_session_absolute_hours * 3600,
    )


@router.post("/login", response_model=SessionResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> SessionResponse:
    """Autentica por JSON y rota la sesión; no devuelve token de sesión ni contraseña."""
    ensure_allowed_origin(request, settings)
    ip = client_ip(request, settings)
    enforce_login_allowed(uow, body.username, ip)
    try:
        principal = authenticate_workshop_credentials(
            body.username, body.password, settings
        )
    except HTTPException:
        # Solo los fallos consumen el límite de 5 intentos por usuario e IP.
        record_login_failure(uow, body.username, ip)
        raise
    if principal.carpenter_id is None:
        record_login_failure(uow, body.username, ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workshop credentials",
        )

    reset_login_failures(uow, body.username, ip)
    previous_token = read_session_token(request)
    if previous_token:
        EndWorkshopSession(uow).execute(previous_token)

    session_token = StartWorkshopSession(uow).execute(principal.carpenter_id)
    csrf_token = new_csrf_token()
    set_session_cookies(
        response,
        session_token=session_token,
        csrf_token=csrf_token,
        settings=settings,
    )
    return _session_payload(
        settings, carpenter_id=int(principal.carpenter_id), csrf_token=csrf_token
    )


@router.get("/session", response_model=SessionResponse)
def read_session(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> SessionResponse:
    """Devuelve la sesión vigente; no crea ni prolonga sesiones inexistentes."""
    token = read_session_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workshop session required",
        )
    carpenter_id = ResolveWorkshopSession(uow).execute(token)
    if carpenter_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired workshop session",
        )

    csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or new_csrf_token()
    set_csrf_cookie(response, csrf_token, settings)
    response.headers["Cache-Control"] = "no-store"
    return _session_payload(
        settings, carpenter_id=int(carpenter_id), csrf_token=csrf_token
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    settings: Settings = Depends(get_settings),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Revoca la sesión y borra las cookies; es idempotente sin sesión."""
    token = read_session_token(request)
    if token:
        enforce_csrf(request, settings)
        EndWorkshopSession(uow).execute(token)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookies(response, settings)
    return response
