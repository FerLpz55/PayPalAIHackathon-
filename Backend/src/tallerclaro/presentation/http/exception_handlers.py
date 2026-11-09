"""Manejadores de excepciones HTTP."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tallerclaro.application.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    ValidationDomainError,
)


def _domain_error_to_status(error: DomainError) -> int:
    mapping = {
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN": status.HTTP_403_FORBIDDEN,
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PAYMENT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "AI_RESPONSE_INVALID": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "BAD_GATEWAY": status.HTTP_502_BAD_GATEWAY,
        "PAYMENT_PROVIDER_ERROR": status.HTTP_502_BAD_GATEWAY,
        "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
        "PAYLOAD_TOO_LARGE": status.HTTP_413_CONTENT_TOO_LARGE,
    }
    return mapping.get(error.code, status.HTTP_400_BAD_REQUEST)


def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    headers = {}
    status_code = _domain_error_to_status(exc)
    if status_code == status.HTTP_401_UNAUTHORIZED:
        headers["WWW-Authenticate"] = "Basic"
    if isinstance(exc, RateLimitedError):
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": exc.message},
        headers=headers if headers else None,
    )


def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    field_errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error.get("loc", []))
        field_errors.append({"field": loc, "message": error.get("msg", "")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "field_errors": field_errors,
        },
    )


def register(app) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
