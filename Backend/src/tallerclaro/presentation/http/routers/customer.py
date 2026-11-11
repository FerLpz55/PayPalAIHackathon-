"""Recuperación autorizada de los recursos del cliente."""

from __future__ import annotations

from fastapi import APIRouter

from tallerclaro.application.use_cases import GetCustomerContext
from tallerclaro.presentation.http.dependencies import CustomerTokenDep, UnitOfWorkDep
from tallerclaro.presentation.http.mappers import (
    to_customer_context_response as _to_customer_context_response,
)
from tallerclaro.presentation.http.schemas.customer import CustomerContextResponse

router = APIRouter(prefix="/api", tags=["customer"])


@router.get("/customer/context")
def get_customer_context(
    principal: CustomerTokenDep,
    uow: UnitOfWorkDep,
) -> CustomerContextResponse:
    """Devuelve cotización, pedido e intentos de pago del token de cliente válido.

    Solo acepta ``X-Customer-Token``/Bearer. Un token inválido responde 401 y
    nunca concede privilegios del taller ni permite recuperar recursos por ID.
    """
    context = GetCustomerContext(uow).execute(principal)
    return _to_customer_context_response(context)
