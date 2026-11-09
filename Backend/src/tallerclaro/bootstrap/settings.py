"""Configuración del servidor."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# `Backend/.env` se resuelve desde la ubicación del paquete, no desde el
# directorio de trabajo. Las variables del proceso siguen teniendo prioridad.
ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

_ENVIRONMENTS = {"development", "test", "release"}
_ENVIRONMENT_ALIASES = {"dev": "development", "prod": "release", "production": "release"}
_PLACEHOLDER_MARKERS = ("change-me", "changeme", "example", "placeholder", "your-")


def _looks_like_placeholder(value: str | None) -> bool:
    """Detecta secretos de plantilla que nunca deben usarse en release."""
    if not value:
        return True
    lowered = value.strip().lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _is_public_https_url(value: str | None) -> bool:
    if not value:
        return False
    parts = urlsplit(value)
    return parts.scheme == "https" and bool(parts.netloc)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALLERCLARO_",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    app_name: str = "TallerClaro API"
    # development | test | release. `release` activa las validaciones estrictas.
    environment: str = "development"

    # Base de datos: URL o campos individuales (ficticios por defecto).
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "TALLERCLARO_DATABASE_URL"),
        description="PostgreSQL URL; si se provee, tiene prioridad sobre los campos individuales.",
    )
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "tallerclaro"
    database_user: str = "tallerclaro_app"
    database_password: str = "change-me"
    database_ssl_mode: str = "prefer"
    database_pool_min_size: int = 2
    database_pool_max_size: int = 10
    # Tiempo máximo para obtener una conexión del pool y caducidad de conexiones inactivas.
    database_pool_acquire_timeout_seconds: float = 10.0
    database_pool_max_idle_seconds: float = 300.0

    # IA
    ai_provider: str = "none"  # none | openai | openrouter
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_base_url: str | None = None

    # Búsqueda de precios de materiales en vivo
    price_lookup_provider: str = "none"  # none | channel3 | web
    price_lookup_api_key: str | None = None
    price_lookup_base_url: str | None = None

    # PayPal
    paypal_mode: str = "none"  # none | sandbox | live
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str | None = None  # Se infiere del modo si no se provee.
    paypal_return_url: str | None = None
    paypal_cancel_url: str | None = None
    paypal_webhook_id: str | None = None
    # Este release solo se aprueba para Sandbox; Live exige habilitación explícita.
    allow_live_payments: bool = False

    # Acceso de demo del taller
    workshop_username: str = "taller"
    workshop_carpenter_id: int = 1
    workshop_password_hash: str = ""
    # Sesiones revocables: inactividad y duración absoluta.
    workshop_session_idle_minutes: int = 30
    workshop_session_absolute_hours: int = 8
    # Basic solo como compatibilidad explícita; las sesiones son el mecanismo por defecto.
    enable_workshop_basic_auth: bool = False

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins",
    )

    # Tokens de enlace de cliente
    customer_token_secret: str = "change-me-secret-min-32-chars-long"
    customer_token_ttl_hours: int = 72

    # Límites y transporte
    max_request_body_bytes: int = 64 * 1024
    # Solo confiar en X-Forwarded-For si un proxy propio lo sobrescribe.
    trust_proxy_headers: bool = False

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        normalized = "development" if value is None else str(value).strip().lower()
        normalized = _ENVIRONMENT_ALIASES.get(normalized, normalized)
        return normalized

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        if value not in _ENVIRONMENTS:
            allowed = ", ".join(sorted(_ENVIRONMENTS))
            raise ValueError(f"environment must be one of: {allowed}")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                return json.loads(v)
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return [str(i) for i in v]
        return ["*"]

    @model_validator(mode="after")
    def validate_release_configuration(self) -> "Settings":
        """Rechaza configuraciones inseguras cuando `environment=release`."""
        if self.environment != "release":
            return self

        problems: list[str] = []

        if not self.cors_origins or "*" in self.cors_origins:
            problems.append("TALLERCLARO_CORS_ORIGINS must list explicit origins in release")
        for origin in self.cors_origins:
            if not _is_public_https_url(origin):
                problems.append(f"CORS origin must be an absolute https URL: {origin}")

        if _looks_like_placeholder(self.workshop_password_hash):
            problems.append("TALLERCLARO_WORKSHOP_PASSWORD_HASH must be a real bcrypt hash in release")
        if _looks_like_placeholder(self.customer_token_secret) or len(self.customer_token_secret) < 32:
            problems.append("TALLERCLARO_CUSTOMER_TOKEN_SECRET must be a real secret of at least 32 characters in release")

        if self.ai_provider != "none" and _looks_like_placeholder(self.ai_api_key):
            problems.append("TALLERCLARO_AI_API_KEY must be configured when an AI provider is enabled")

        if self.price_lookup_provider != "none" and _looks_like_placeholder(self.price_lookup_api_key):
            problems.append("TALLERCLARO_PRICE_LOOKUP_API_KEY must be configured when a price provider is enabled")

        if self.paypal_mode in {"sandbox", "live"}:
            if _looks_like_placeholder(self.paypal_client_id):
                problems.append("TALLERCLARO_PAYPAL_CLIENT_ID is required when PayPal is enabled")
            if _looks_like_placeholder(self.paypal_client_secret):
                problems.append("TALLERCLARO_PAYPAL_CLIENT_SECRET is required when PayPal is enabled")
            if not _is_public_https_url(self.paypal_return_url):
                problems.append("TALLERCLARO_PAYPAL_RETURN_URL must be an absolute https URL")
            if not _is_public_https_url(self.paypal_cancel_url):
                problems.append("TALLERCLARO_PAYPAL_CANCEL_URL must be an absolute https URL")
            if self.paypal_mode == "live" and not self.allow_live_payments:
                problems.append(
                    "PayPal live mode is outside this release; set TALLERCLARO_ALLOW_LIVE_PAYMENTS=true explicitly"
                )

        if problems:
            raise ValueError("Invalid release configuration: " + "; ".join(problems))
        return self

    @property
    def is_release(self) -> bool:
        return self.environment == "release"

    @property
    def database_dsn(self) -> str:
        if self.database_url:
            # Algunos enlaces copiados contienen @ sin escapar en la contraseña.
            # Separar por el último @ conserva el host y no recodifica %40.
            parts = urlsplit(self.database_url)
            credentials, separator, host = parts.netloc.rpartition("@")
            if separator and ":" in credentials:
                user, password = credentials.split(":", 1)
                authority = f"{user}:{password.replace('@', '%40')}@{host}"
                return urlunsplit(parts._replace(netloc=authority))
            return self.database_url
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"?sslmode={self.database_ssl_mode}"
        )

    @property
    def paypal_api_base(self) -> str | None:
        if self.paypal_base_url:
            return self.paypal_base_url
        if self.paypal_mode == "sandbox":
            return "https://api.sandbox.paypal.com"
        if self.paypal_mode == "live":
            return "https://api.paypal.com"
        return None
