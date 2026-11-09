"""Esquemas HTTP de autenticación del taller."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class SessionResponse(BaseModel):
    """Información de sesión; nunca incluye el token de sesión ni la contraseña."""

    authenticated: bool
    carpenter_id: int | None = None
    username: str | None = None
    csrf_token: str | None = None
    idle_timeout_seconds: int
    absolute_timeout_seconds: int
