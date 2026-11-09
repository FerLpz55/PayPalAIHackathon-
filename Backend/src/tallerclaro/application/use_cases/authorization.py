"""Reglas compartidas de autorización de recursos para casos de uso."""

from __future__ import annotations

from tallerclaro.application.dtos import AccessPrincipal
from tallerclaro.application.exceptions import ForbiddenError
from tallerclaro.application.interfaces import UnitOfWork
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


class StartWorkshopSession:
    """Crea una sesión opaca nueva (rotación en cada inicio de sesión)."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, carpenter_id: CarpenterId) -> str:
        return self._uow.execute_sql(lambda uow: uow.sessions.create(carpenter_id))


class ResolveWorkshopSession:
    """Devuelve el taller de una sesión vigente o ``None`` si no es utilizable."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, token: str) -> CarpenterId | None:
        with self._uow:
            return self._uow.sessions.verify(token)


class EndWorkshopSession:
    """Revoca una sesión; es idempotente ante tokens desconocidos o ya revocados."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, token: str) -> bool:
        return bool(
            self._uow.execute_sql(lambda uow: uow.sessions.revoke(token))
        )
