"""Dependencias de autorización HTTP."""

from __future__ import annotations

import base64
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.ports import UnitOfWork
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId, CustomerId, QuoteId

security = HTTPBasic(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_unit_of_work(request: Request) -> UnitOfWork:
    factory = request.app.state.uow_factory
    return factory() if callable(factory) else factory


SettingsDep = Annotated[Settings, Depends(get_settings)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


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
    valid_user = secrets.compare_digest(credentials.username, settings.workshop_username)
    valid_pass = secrets.compare_digest(credentials.password, settings.workshop_password)
    if not (valid_user and valid_pass):
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
    token = x_customer_token or request.headers.get("x-customer-token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer token required",
        )

    with uow:
        result = uow.tokens.verify(token)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired customer token",
        )
    customer_id, quote_id = result
    return AccessPrincipal(
        kind="customer",
        customer_id=customer_id,
        quote_id=quote_id,
    )


def require_quote_or_workshop_principal(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(security),
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> AccessPrincipal:
    # 1. Probar Customer Token
    token = request.headers.get("x-customer-token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

    if token:
        with uow:
            result = uow.tokens.verify(token)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired customer token",
            )
        customer_id, quote_id = result
        return AccessPrincipal(
            kind="customer",
            customer_id=customer_id,
            quote_id=quote_id,
        )

    # 2. Probar credenciales del taller (HTTPBasicCredentials)
    if credentials is not None:
        valid_user = secrets.compare_digest(credentials.username, settings.workshop_username)
        valid_pass = secrets.compare_digest(credentials.password, settings.workshop_password)
        if not (valid_user and valid_pass):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid workshop credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return AccessPrincipal(
            kind="workshop",
            carpenter_id=CarpenterId(settings.workshop_carpenter_id),
        )

    # 3. Probar Authorization header en caso de que HTTPBasic no se haya poblado
    raw_auth = request.headers.get("authorization", "")
    if raw_auth.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(raw_auth[6:].strip()).decode("utf-8")
            username, _, password = decoded.partition(":")
            valid_user = secrets.compare_digest(username, settings.workshop_username)
            valid_pass = secrets.compare_digest(password, settings.workshop_password)
            if not (valid_user and valid_pass):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid workshop credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return AccessPrincipal(
                kind="workshop",
                carpenter_id=CarpenterId(settings.workshop_carpenter_id),
            )
        except HTTPException:
            raise
        except Exception:
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
