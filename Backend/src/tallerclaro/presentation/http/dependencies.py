"""Dependencias de la capa de presentación HTTP.

Centraliza la resolución de configuración, unidad de trabajo, servicios de IA,
procesadores de pago y autenticación (sesión de taller con cookie, token de
enlace de cliente y Basic solo como compatibilidad explícita).
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.interfaces import (
    AccountingAssistant,
    AIService,
    PaymentProcessor,
    PriceLookupService,
    UnitOfWork,
)
from tallerclaro.application.use_cases import ResolveWorkshopSession, VerifyCustomerToken
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId
from tallerclaro.infrastructure.security.workshop_auth import verify_workshop_credentials
from tallerclaro.presentation.http.session_cookies import (
    enforce_csrf,
    read_session_token,
)

security = HTTPBasic(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_unit_of_work(request: Request) -> UnitOfWork:
    factory = request.app.state.uow_factory
    return factory() if callable(factory) else factory


def get_ai_service(request: Request) -> AIService:
    return request.app.state.ai_service


def get_payment_processor(request: Request) -> PaymentProcessor:
    return request.app.state.payment_processor


def get_accounting_assistant(request: Request) -> AccountingAssistant:
    return request.app.state.accounting_assistant


def get_price_lookup_service(request: Request) -> PriceLookupService:
    service = getattr(request.app.state, "price_lookup_service", None)
    if service is None:
        from tallerclaro.infrastructure.ai.price_lookup import build_price_lookup_service
        service = build_price_lookup_service(request.app.state.settings)
        request.app.state.price_lookup_service = service
    return service


SettingsDep = Annotated[Settings, Depends(get_settings)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
AIServiceDep = Annotated[AIService, Depends(get_ai_service)]
PaymentProcessorDep = Annotated[PaymentProcessor, Depends(get_payment_processor)]
AccountingAssistantDep = Annotated[AccountingAssistant, Depends(get_accounting_assistant)]
PriceLookupServiceDep = Annotated[PriceLookupService, Depends(get_price_lookup_service)]


# --- Funciones auxiliares de autenticación (Single Responsibility Principle) ---


def _verify_workshop_credentials(username: str, password: str, settings: Settings) -> bool:
    """Resuelve credenciales HTTP; la verificación criptográfica vive en infraestructura."""
    return verify_workshop_credentials(username, password, settings)


def _extract_customer_token(request: Request, x_customer_token: str | None = None) -> str | None:
    token = x_customer_token or request.headers.get("x-customer-token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    return token or None


def _parse_basic_auth_header(auth_header: str) -> tuple[str, str] | None:
    if not auth_header.lower().startswith("basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header[6:].strip()).decode("utf-8")
        username, sep, password = decoded.partition(":")
        if not sep:
            return None
        return username, password
    except Exception:
        return None


def _unauthorized(detail: str, *, basic_challenge: bool = True) -> HTTPException:
    headers = {"WWW-Authenticate": "Basic"} if basic_challenge else None
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=headers,
    )


def authenticate_workshop_credentials(
    username: str, password: str, settings: Settings
) -> AccessPrincipal:
    """Verifica usuario/contraseña y devuelve el actor del taller."""
    if not _verify_workshop_credentials(username, password, settings):
        raise _unauthorized("Invalid workshop credentials")
    return AccessPrincipal(
        kind="workshop",
        carpenter_id=CarpenterId(settings.workshop_carpenter_id),
    )


def _authenticate_customer_token(token: str, uow: UnitOfWork) -> AccessPrincipal:
    principal = VerifyCustomerToken(uow).execute(token)
    if principal is None:
        raise _unauthorized("Invalid or expired customer token", basic_challenge=False)
    return principal


def _authenticate_workshop_session(
    request: Request, uow: UnitOfWork, settings: Settings
) -> AccessPrincipal | None:
    """Resuelve la cookie de sesión; aplica CSRF y origen en métodos inseguros."""
    token = read_session_token(request)
    if not token:
        return None
    enforce_csrf(request, settings)
    carpenter_id = ResolveWorkshopSession(uow).execute(token)
    if carpenter_id is None:
        raise _unauthorized(
            "Invalid or expired workshop session", basic_challenge=False
        )
    return AccessPrincipal(kind="workshop", carpenter_id=carpenter_id)


def _authenticate_basic_if_enabled(
    request: Request,
    credentials: HTTPBasicCredentials | None,
    settings: Settings,
) -> AccessPrincipal | None:
    """Basic solo se acepta con compatibilidad explícita habilitada."""
    if not settings.enable_workshop_basic_auth:
        return None
    if credentials is not None:
        return authenticate_workshop_credentials(
            credentials.username, credentials.password, settings
        )
    raw_auth = request.headers.get("authorization", "")
    parsed_basic = _parse_basic_auth_header(raw_auth)
    if parsed_basic is not None:
        return authenticate_workshop_credentials(*parsed_basic, settings)
    if raw_auth.lower().startswith("basic "):
        raise _unauthorized("Invalid workshop credentials")
    return None


# --- Dependencias públicas de autorización ---


def require_workshop_credentials(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    principal = _authenticate_workshop_session(request, uow, settings)
    if principal is not None:
        return principal

    basic_principal = _authenticate_basic_if_enabled(request, credentials, settings)
    if basic_principal is not None:
        return basic_principal

    raise _unauthorized(
        "Workshop session required",
        basic_challenge=settings.enable_workshop_basic_auth,
    )


def require_customer_token(
    request: Request,
    x_customer_token: Annotated[str | None, Header(alias="X-Customer-Token")] = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    token = _extract_customer_token(request, x_customer_token)
    if not token:
        raise _unauthorized("Customer token required", basic_challenge=False)
    return _authenticate_customer_token(token, uow)


def require_quote_or_workshop_principal(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    # Un token de cliente inválido nunca degrada a privilegios del taller.
    token = _extract_customer_token(request)
    if token:
        return _authenticate_customer_token(token, uow)

    principal = _authenticate_workshop_session(request, uow, settings)
    if principal is not None:
        return principal

    basic_principal = _authenticate_basic_if_enabled(request, credentials, settings)
    if basic_principal is not None:
        return basic_principal

    raise _unauthorized(
        "Authentication required",
        basic_challenge=settings.enable_workshop_basic_auth,
    )


WorkshopCarpenterDep = Annotated[AccessPrincipal, Depends(require_workshop_credentials)]
CustomerTokenDep = Annotated[AccessPrincipal, Depends(require_customer_token)]
PrincipalDep = Annotated[AccessPrincipal, Depends(require_quote_or_workshop_principal)]
