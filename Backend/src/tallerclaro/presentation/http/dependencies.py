"""Dependencias de autorización HTTP."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from tallerclaro.application.ports import UnitOfWork
from tallerclaro.bootstrap.settings import Settings
from tallerclaro.domain.entities import CarpenterId, CustomerId, QuoteId
from tallerclaro.infrastructure.db.unit_of_work import PostgresUnitOfWork
from tallerclaro.infrastructure.security.token_service import CustomerTokenService

security = HTTPBasic(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_unit_of_work(request: Request) -> UnitOfWork:
    return request.app.state.uow_factory


def require_workshop_credentials(
    credentials: HTTPBasicCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> CarpenterId:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workshop credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    valid_user = secrets.compare_digest(credentials.username, settings.workshop_username)
    # En demo se compara contra hash real con passlib; aquí se usa un placeholder.
    valid_pass = secrets.compare_digest(credentials.password, "demo-password")
    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid workshop credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return CarpenterId(1)


def require_customer_token(
    request: Request,
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings),
) -> tuple[CustomerId, QuoteId]:
    token = request.headers.get("x-customer-token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer token required",
        )
    with uow as uow_ctx:
        conn = uow_ctx.get_connection()
        service = CustomerTokenService(conn, settings.customer_token_secret, settings.customer_token_ttl_hours)
        result = service.verify(token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired customer token",
        )
    return result
