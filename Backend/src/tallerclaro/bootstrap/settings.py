"""Configuración del servidor."""

from pathlib import Path

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Directorio Backend/, independiente del directorio de trabajo.
_BACKEND_DIR = Path(__file__).resolve().parents[3]

# Se cargan ambos archivos. Los archivos posteriores en la tupla tienen
# prioridad, así que .env.example aporta los valores por defecto y .env los
# sobreescribe con las credenciales reales (por ejemplo, la URL de Supabase).
_ENV_EXAMPLE_FILE = _BACKEND_DIR / ".env.example"
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TALLERCLARO_",
        env_file=(_ENV_EXAMPLE_FILE, _ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    workshop_password: str = "demo-password"
    workshop_carpenter_id: int = 1
    workshop_password_hash: str = (
        "$2b$12$invalidplaceholderhash"  # bcrypt ficticio; reemplazar en producción.
    )

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
