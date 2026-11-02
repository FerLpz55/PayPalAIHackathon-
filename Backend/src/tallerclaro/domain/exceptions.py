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
