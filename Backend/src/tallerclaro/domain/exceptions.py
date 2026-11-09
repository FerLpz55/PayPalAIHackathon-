"""Excepciones del dominio."""


class DomainError(Exception):
    """Error base del dominio."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class NotFoundError(DomainError):
    """Recurso no encontrado."""

    def __init__(self, resource: str, identifier: object) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} with identifier {identifier} was not found",
        )


class ConflictError(DomainError):
    """Conflicto de estado o duplicado."""

    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(code=code, message=message)


class ValidationDomainError(DomainError):
    """Entrada de dominio inválida."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(code="VALIDATION_ERROR", message=message)


class AuthorizationError(DomainError):
    """No autorizado para operar sobre el recurso."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(code="UNAUTHORIZED", message=message)


class ForbiddenError(DomainError):
    """Acceso prohibido al recurso."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(code="FORBIDDEN", message=message)


class ServiceUnavailableError(DomainError):
    """Dependencia externa o infraestructura no disponible."""

    def __init__(self, message: str = "Service temporarily unavailable") -> None:
        super().__init__(code="SERVICE_UNAVAILABLE", message=message)


class RateLimitedError(DomainError):
    """Se superó un límite de uso; el cliente debe reintentar más tarde."""

    def __init__(self, retry_after: int, message: str = "Too many requests") -> None:
        self.retry_after = max(1, int(retry_after))
        super().__init__(code="RATE_LIMITED", message=message)

