"""Esquemas comunes de respuesta."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    field_errors: list[dict[str, str]] | None = None
