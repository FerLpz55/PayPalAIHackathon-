"""Reglas compartidas de autorización de recursos para casos de uso."""

from __future__ import annotations

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.exceptions import ForbiddenError
from tallerclaro.domain.entities import CarpenterId, QuoteId


def authorize_workshop_or_customer(
    principal: AccessPrincipal | None,
    *,
    carpenter_id: CarpenterId,
    quote_id: QuoteId | None,
    resource_name: str,
) -> None:
    """Verifica que el actor autenticado pertenezca al taller dueño o al cliente de la cotización.

    Si ``principal`` es ``None`` (uso interno o pruebas unitarias directas sin actor),
    no aplica restricción.
    """
    if principal is None:
        return

    if principal.is_workshop:
        if principal.carpenter_id is not None and carpenter_id != principal.carpenter_id:
            raise ForbiddenError(f"Not authorized to access this {resource_name}")
        return

    if principal.is_customer:
        if quote_id is None or principal.quote_id != quote_id:
            raise ForbiddenError(f"Not authorized to access this {resource_name}")
        return

    raise ForbiddenError("Invalid principal")

