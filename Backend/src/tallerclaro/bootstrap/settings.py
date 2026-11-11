"""Configuración del servidor."""

from urllib.parse import urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALLERCLARO_",
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    app_name: str = "TallerClaro API"

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

    # Acceso de demo del taller
    workshop_username: str = "taller"
    workshop_carpenter_id: int = 1
    workshop_password_hash: str = ""

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins",
    )

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

    # Tokens de enlace de cliente
    customer_token_secret: str = "change-me-secret-min-32-chars-long"
    customer_token_ttl_hours: int = 72

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
