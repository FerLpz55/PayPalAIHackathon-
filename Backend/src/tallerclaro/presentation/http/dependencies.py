"""Dependencias de la capa de presentación HTTP.

Centraliza la resolución de configuración, unidad de trabajo, servicios de IA,
procesadores de pago y autenticación (HTTP Basic y token de enlace de cliente).
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.interfaces import AIService, PaymentProcessor, UnitOfWork
from tallerclaro.application.use_cases import VerifyCustomerToken
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId
from tallerclaro.infrastructure.security.workshop_auth import verify_workshop_credentials

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


SettingsDep = Annotated[Settings, Depends(get_settings)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
AIServiceDep = Annotated[AIService, Depends(get_ai_service)]
PaymentProcessorDep = Annotated[PaymentProcessor, Depends(get_payment_processor)]


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


# --- Dependencias públicas de autorización ---

def require_workshop_credentials(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workshop credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if not _verify_workshop_credentials(credentials.username, credentials.password, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workshop credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return AccessPrincipal(
        kind="workshop",
        carpenter_id=CarpenterId(settings.workshop_carpenter_id),
    )


def require_customer_token(
    request: Request,
    x_customer_token: Annotated[str | None, Header(alias="X-Customer-Token")] = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    token = _extract_customer_token(request, x_customer_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer token required",
        )

    principal = VerifyCustomerToken(uow).execute(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired customer token",
        )
    return principal


def require_quote_or_workshop_principal(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    # 1. Probar Customer Token
    token = _extract_customer_token(request)
    if token:
        principal = VerifyCustomerToken(uow).execute(token)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired customer token",
            )
        return principal

    # 2. Probar credenciales del taller (HTTPBasicCredentials)
    if credentials is not None:
        if not _verify_workshop_credentials(credentials.username, credentials.password, settings):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid workshop credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return AccessPrincipal(
            kind="workshop",
            carpenter_id=CarpenterId(settings.workshop_carpenter_id),
        )

    # 3. Probar Authorization header directo en caso de que HTTPBasic no se haya poblado
    raw_auth = request.headers.get("authorization", "")
    parsed_basic = _parse_basic_auth_header(raw_auth)
    if parsed_basic is not None:
        username, password = parsed_basic
        if not _verify_workshop_credentials(username, password, settings):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid workshop credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return AccessPrincipal(
            kind="workshop",
            carpenter_id=CarpenterId(settings.workshop_carpenter_id),
        )
    elif raw_auth.lower().startswith("basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workshop credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Basic"},
    )


WorkshopCarpenterDep = Annotated[AccessPrincipal, Depends(require_workshop_credentials)]
CustomerTokenDep = Annotated[AccessPrincipal, Depends(require_customer_token)]
PrincipalDep = Annotated[AccessPrincipal, Depends(require_quote_or_workshop_principal)]
