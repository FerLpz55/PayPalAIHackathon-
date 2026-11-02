"""Excepciones de la capa de aplicación."""

from tallerclaro.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationDomainError,
)

__all__ = [
    "DomainError",
    "NotFoundError",
    "ConflictError",
    "ValidationDomainError",
    "AuthorizationError",
]
