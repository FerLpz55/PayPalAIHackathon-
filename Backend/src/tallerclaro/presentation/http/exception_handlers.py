"""Manejadores de excepciones HTTP."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from tallerclaro.application.exceptions import (
    AuthorizationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationDomainError,
)


def _domain_error_to_status(error: DomainError) -> int:
    mapping = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    }
    return mapping.get(error.code, status.HTTP_400_BAD_REQUEST)


def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=_domain_error_to_status(exc),
        content={"code": exc.code, "message": exc.message},
    )


def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    field_errors = []
    for error in exc.errors():
        loc = ".".join(str(x) for x in error.get("loc", []))
        field_errors.append({"field": loc, "message": error.get("msg", "")})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "field_errors": field_errors,
        },
    )


def register(app) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
