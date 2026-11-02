"""Configuración del servidor."""

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TALLERCLARO_", extra="ignore")

    app_name: str = "TallerClaro API"

    # Base de datos: URL o campos individuales (ficticios por defecto).
    database_url: str | None = Field(
        default=None,
        description="PostgreSQL URL; si se provee, se usan los campos individuales.",
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

    # PayPal
    paypal_mode: str = "none"  # none | sandbox | live
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_base_url: str | None = None  # Se infiere del modo si no se provee.

    # Acceso de demo del taller
    workshop_username: str = "taller"
    workshop_password_hash: str = (
        "$2b$12$invalidplaceholderhash"  # bcrypt ficticio; reemplazar en producción.
    )

    # Tokens de enlace de cliente
    customer_token_secret: str = "change-me-secret-min-32-chars-long"
    customer_token_ttl_hours: int = 72

    @property
    def database_dsn(self) -> str:
        if self.database_url:
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
