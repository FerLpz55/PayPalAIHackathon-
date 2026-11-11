"""Excepciones de la capa de aplicación."""

from tallerclaro.domain.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
    ValidationDomainError,
)

__all__ = [
    "DomainError",
    "NotFoundError",
    "ConflictError",
    "ValidationDomainError",
    "AuthorizationError",
    "ForbiddenError",
    "ServiceUnavailableError",
    "RateLimitedError",
]
